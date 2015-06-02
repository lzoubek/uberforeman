import logging, re, time, copy
from threading import Lock, Thread
from .client import OvirtClient,getOrFail,getOrNone
from .hostready import JonBCHostReady,ImageBasedVMHostReady
import json, uuid
from .defaults import VM_DEFAULT, FOREMAN_DEFAULT
from .util import run_parallel, run_parallel_bool

class AttrResolveException(Exception):
    pass

class Uberforeman(object):

    def __init__(self,foreman,setup,name,hostDefaults={}):
        self.log = logging.getLogger("Foreman")
        self.log.setLevel(logging.INFO)
        if len(self.log.handlers) == 0:
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            ch.setFormatter(formatter)
            self.log.addHandler(ch)
        self.foreman = foreman
        self.vmChecker = JonBCHostReady(foreman)
        self.setup = setup
        self.name = name
        if hostDefaults is None:
                hostDefaults = {}
        self._applyDefaults(hostDefaults)
        self._validateSetup()

    def _expr(self,expr):
        m = re.search('\$host:(?P<name>[^\.]+).(?P<attr>[^$]+)',expr)
        if m:
            return 'host',m.group('name'),m.group('attr')
        m = re.search('\$global:(?P<name>[^$:]+)(:|$)',expr)
        if m:
            return 'global',m.group('name'),m.group(0)
    
    def _resolveExpr(self,value):
        expr = self._expr(value)
        if expr: #we have expression
            _type,name,attr = expr
            if _type == 'host':
                vm_list = list(filter(lambda x:x['name']==name,self.setup['hosts']))
                if len(vm_list) != 1:
                    raise Exception('Error resolving value for expression %s' % value)
                if attr not in vm_list[0]:
                    raise AttrResolveException('Attribute %s is not yet known for host %s' % (attr,vm_list[0]['name']))
                value = vm_list[0][attr]
            elif _type == 'global':
                value = self.setup['global'][name]
        return value


    def _applyDefaults(self,hostDefaults):
        if not 'default-host' in self.setup.keys():
            self.setup['default-host'] = {}
        default = copy.deepcopy(VM_DEFAULT)
        default.update(hostDefaults)
        default.update(self.setup['default-host'])
        self.setup['default-host'] = default
        vms = []
        for vm in self.setup['hosts']:
            host = copy.deepcopy(default)
            host.update(vm)
            vms.append(host)
        self.setup['hosts'] = vms

    def validateSetup(self):
        """Validates setup by checking state/existence of hosts and referenced resources"""
        self.log.info('Validating setup ... please wait')
        f = self.foreman
        for vm in self.setup['hosts']:
            self.log.info(' Validating %s', vm['name'])
            vm['status'] = {}
            remote = vm['status']['remote'] = getOrNone(self.foreman.hosts)(name='%s.%s' % (vm['name'],vm['domain']))
            if remote:
                # copy IP directly to VM so we can access it easily
                vm['ip'] = remote['ip']
            local = vm['status']['local'] = copy.deepcopy(FOREMAN_DEFAULT)
            local['name'] = vm['name']
            hostgroup = getOrFail(f.hostgroups)(title=vm['hostGroup'])
            local['hostgroup_id'] = hostgroup['id']
            local['subnet_id'] = hostgroup['subnet_id']
            cr = getOrFail(f.computeResources)(name=vm['computeResource'])
            assert cr['provider'] == 'oVirt', "Invalid computeResource=%s detected, only 'oVirt' is supported" % cr['provider']
            local['compute_resource_id'] = cr['id']
            if vm['image'] and len(vm['image']) > 0:
                image = getOrFail(self.foreman.images)(compute_resource=cr,name=vm['image'])
                local['image_id'] = image['id']
                local['provision_method'] = 'image'
                local['operatingsystem_id'] = image['operatingsystem_id'] # take op sys from image
                local['compute_attributes']['start'] = '1' # start immediatelly to finish orchestration task
                local['compute_attributes']['image_id'] = image['uuid'] # pass oVirt image UUID to compute_attributes
            local['progress_report_id'] = str(uuid.uuid4()) # generate UUID to track task
            cr = OvirtClient.fromComputeResource(cr)
            local['domain_id'] = getOrFail(f.domains)(name=vm['domain'])['id']
            local['compute_attributes']['cluster'] = getOrFail(cr.clusters)(name=vm['cluster'])['id']
            local['compute_attributes']['volumes_attributes']['0']['storage_domain'] = getOrFail(cr.storages)(name=vm['storage'])['id']
            local['compute_attributes']['volumes_attributes']['0']['size_gb'] = vm['disk']
            local['compute_attributes']['memory'] = int(vm['ram'] * 1024 * 1024 * 1024)
            local['compute_attributes']['cores'] = int(vm['cpus'])


    def _validateSetup(self):
        """Validates setup file format - it's just a syntactic check of correct keys/values"""
        s = self.setup
        assert 'hosts' in s.keys(), "hosts array is required"
    
        def _typeNumAttrs(host):
            for attr in ['order','clones','cpus','ram']:
                try:
                    host[attr] = int(host[attr])
                except:
                    pass
        
        def evalGlobals(setup, obj):
            for key, value in obj.items():
                if isinstance(value, str):
                    expr = self._expr(value)
                    if expr: # it is an expression
                        _type, name, attr = expr
                        if _type == 'host':
                            assert attr in ['ip'], "invalid expression attribute"
                        if _type == 'global':
                            assert 'global' in s.keys(), "refered to global %s but no globals defined" % name 
                            assert name in setup['global'].keys(), "refered to global %s but this global is not defined" % name
                            obj[key] = obj[key].replace(attr, setup['global'][name])

        for vm in s['hosts']:
            # extract global variables
            evalGlobals(s,vm)
            evalGlobals(s,vm['params'])
            _typeNumAttrs(vm)

            if not 'order' in vm.keys():
                vm['order'] = 0
            assert type(vm['order']) == int, "order attribute must be integer"
            assert type(vm['clones']) == int, "clones attribute must be integer"
            assert vm['clones'] >= 0, "clones attribute must be positive integer"
            assert 'name' in vm.keys() and 'hostGroup' in vm.keys(), "name and hostGroup attributes are required"
            assert type(vm['cpus']) == int and vm['cpus'] > 0, "cpus attribute must be integer and value greater than 0"
            if not 'params' in vm.keys():
                vm['params'] = {}
            assert type(vm['params']) == type({}), "params attribute must be dict"

        # expand clones
        for host in s['hosts']:
            for c in range(host['clones']):
                clone = copy.deepcopy(host)
                clone['name'] += str(c+1)
                clone['clones'] = 0
                s['hosts'].append(clone)

        s['hosts'] = sorted(s['hosts'],key=lambda x: x['order'])
        assert len(set(map(lambda x: x['name'],s['hosts']))) == len(s['hosts']), "name attr of VM in setup must me unique"
        
    def _showOutOfSyncWarnings(self,vm):
        local = vm['status']['local']
        remote = vm['status']['remote']
        # detect hostgroup change
        if local['hostgroup_id'] != remote['hostgroup_id']:
            remoteHG = self.foreman.hostgroups(id=remote['hostgroup_id'])[0]['label']                
            self.log.warn('HostGroup is out of sync, consider --force-install, foreman reports : %s',remoteHG)
        # detect param additions/removals and value changes
        remote_params = []
        if 'parameters' in remote.keys():
            remote_params =  map(lambda p:{p['name']:p['value']},remote['parameters'])
        rp = {}
        [rp.update(x) for x in remote_params]
        lp = {}
        diff = {}
        for key,value in vm['params'].items():
            lp[key] = self._resolveExpr(value)
        if hasattr(lp,'viewitems'): # python 2.6
            diff = dict(lp.viewitems() ^ rp.viewitems())
        else: # python 3.x
            diff = dict(lp.items() ^ rp.items())
        if len(diff) > 0:
            self.log.warn('Parameter values are out of sync, consider --force-install, server values:')
            for key,value in diff.items():
                if key in lp and key in rp:
                    self.log.warn(' changed : %s=%s', key, value)
                elif key in lp:
                    self.log.warn(' missing : %s=%s', key, value)
                elif key in rp:
                    self.log.warn(' added   : %s=%s', key, value)
    def dump(self):
        for vm in self.setup['hosts']:
            del vm['status']
        print(json.dumps(self.setup,indent=2))

    def status(self):
        sep = '-------------------------------------------'
        self.log.info("Status for setup : %s", self.name)
        self.log.info(sep)
        for vm in self.setup['hosts']:
            exists = vm['status']['remote'] != None
            power = 'unknown'
            if exists:
                power = self.foreman.power(vm['status']['remote']['id'],'state').json()['power']
            self.log.info(' VM name     : %s',vm['name'])
            self.log.info(' Order/phase : %d',vm['order'])
            self.log.info(' HostGroup   : %s',self.foreman.hostgroups(title=vm['hostGroup'])[0]['title'])
            if exists:
                self.log.info(' Hostname    : %s.%s',vm['name'],vm['domain'])
                self.log.info(' IP          : %s',vm['ip'])
                self.log.info(' Building    : %r',vm['status']['remote']['build'])
                self.log.info(' State       : %s', self.vmChecker.getStatus(vm['ip']))
                self.log.info(' Power       : %s', power)
                if vm['status']['remote']['provision_method'] == 'image':
                    self.log.info(' Image       : %s'% vm['status']['remote']['image_name'])
                self._showOutOfSyncWarnings(vm)
            else:
                self.log.info(' VM does not exist in foreman, run --install')
            self.log.info(sep)

    def install(self):
        self.log.info("Installing setup : %s" % self.name)
        if len(self.setup['hosts']) == 0:
            self.log.info('Empty setup?')
            return
        
        def trackTask(uuid):
            time.sleep(10)
            hr = ImageBasedVMHostReady(self.foreman,uuid)
            hr.waitForInstalled(None,None)

        def installHost(vm):
            with lock:
                exists = vm['status']['remote'] != None
            if exists:
                self.log.info('host %s already exists', vm['name'])
                return True
            else:
                index = 0
                for key,value in vm['params'].items():
                    resolved = False
                    while resolved == False:
                        try:
                            with lock:
                                value = self._resolveExpr(value)
                                resolved = True
                        except AttrResolveException:
                            # refering to host attr which is not yet ready .. waiting 
                            time.sleep(1)
                            #self.log.info('sleeping because waiting for %s' % value)

                    param = {'name':key,'value':value,'reference_id':0,'nested':''}
                    vm['status']['local']['host_parameters_attributes'][str(index)] = param
                    index+=1

                self.log.info('Installing %s ..', vm['name'])
                thread = Thread(target = trackTask, args = (vm['status']['local']['progress_report_id'], ))
                thread.daemon = True
                thread.start()
                r = self.foreman.post('/api/hosts',{'host':vm['status']['local']})
                if r.status_code != 200:
                    self.log.error('server returned %d : %s',r.status_code,r.text)
                    raise Exception('failed to install host')
                self.log.info('host %s created in foreman',vm['name'])
                with lock:
                    vm['status']['remote'] = r.json()
                    vm['ip'] = vm['status']['remote']['ip']
                    if thread.isAlive():
                        thread.join()
                if vm['status']['local']['provision_method'] == 'image':
                    self.log.info('Waiting for %s (image-based) to get installed...', vm['name'])
                    self.vmChecker.waitForInstalled(vm['ip'],vm['name'])
                    self.log.info('Host %s is installed' %vm['name'])
                return True

        lock = Lock()
        phase = self.setup['hosts'][0]['order']
        to_install = len(self.setup['hosts'])
        success = True
        while to_install > 0:
            hosts = list(filter(lambda x:x['order'] == phase,self.setup['hosts']))
            to_install -= len(hosts)
            self.log.info('Installing phase %d',phase)
            phase += 1
            success &= run_parallel_bool(installHost, map(lambda x: (x,), hosts))
            if not success:
                self.log.error('Failed to start/install several hosts')
                return
        if success:
            self.log.info('Setup deployed to foreman')
            self.start()


    def _stopHost(self,vm):    
        if vm['status']['remote']:
            self.log.info('Power of %s' %vm['name'])
            r = self.foreman.power(vm['status']['remote']['id'],'stop')
            if r.status_code != 200:
                self.log.error('Failed to stop %s, server returned %d : %s',vm['name'],r.status_code,r.text)
            else:
                self.log.info('VM %s was stopped', vm['name'])
        else:
            self.log.warn('VM %s does not exist in foreman',vm['name'])

    def stop(self):
        self.log.info("Power off setup : %s" % self.name)
        run_parallel(self._stopHost, map(lambda x: (x,), self.setup['hosts']))
        self.log.info('Setup powered off')
    
    def destroy(self):
        self.log.info('Destroy setup: %s',self.name)
        def destroyHost(vm):
            if vm['status']['remote']:
                self.log.info(' Destroying %s' %vm['name'])
                r = self.foreman.delete('/api/hosts/%d' % vm['status']['remote']['id'])
                if r.status_code != 200:
                    self.log.error('Failed to destroy %s, server returned %d : %s',vm['name'],r.status_code,r.text)
                with lock:
                    vm['status']['remote'] = None
                    del vm['ip']
            else:
                self.log.warn('Host %s does not exist in foreman',vm['name'])
        
        lock = Lock()
        run_parallel(destroyHost, map(lambda x: (x,), self.setup['hosts']))
        self.log.info('Setup destroyed')
        
    def _startHost(self,vm):
        exists = vm['status']['remote'] != None
        if not exists:
            raise Exception('VM %s does not exist in foreman, use --install' % vm['name'])
        power = self.foreman.power(vm['status']['remote']['id'],'state').json()['power']
        installed = self.vmChecker.isInstalled(vm['ip'])
        if power == 'up' and installed:
            self.log.info('host %s is already installed', vm['name'])
            return True
        elif power == 'up':
            self.log.info('Waiting for %s to get installed...', vm['name'])
            self.vmChecker.waitForInstalled(vm['ip'],vm['name'])
            self.log.info('Host %s is installed' %vm['name'])
            return True
        self.log.info('Power on %s' %vm['name'])
        r = self.foreman.power(vm['status']['remote']['id'],'start')

        def needs_wait(r):
            """return true if message returned by foreman indicates that we just need to wait to get power on
            action succeed"""
            if r.status_code != 500:
                return False
            try:
                msg = r.json()
                if 'error' in msg.keys() and 'message' in msg['error'].keys():
                    if msg['error']['message'].find('Please try again in a few minutes') > 0:
                        self.log.warning('Host failed to start : %s',msg['error']['message'])
                        self.log.info('Obeying, waiting and retrying...')
                        return True
            except: # just in case foreman does not return JSON
                pass

        while needs_wait(r):
            time.sleep(5)
            r = self.foreman.power(vm['status']['remote']['id'],'start')
        if r.status_code != 200:
            self.log.error('Failed to start %s, server returned %d : %s',vm['name'],r.status_code,r.text)
        else:
            self.log.info('Waiting for %s to get installed...', vm['name'])
            self.vmChecker.waitForInstalled(vm['ip'],vm['name'])
            self.log.info('Host %s is installed' %vm['name'])
            return True

    def start(self):
        self.log.info("Starting setup : %s" % self.name)
        if len(self.setup['hosts']) == 0:
            self.log.info('Empty setup?')
            return
        phase = self.setup['hosts'][0]['order']
        to_start = len(self.setup['hosts'])
        while to_start > 0:
            hosts = list(filter(lambda x:x['order'] == phase,self.setup['hosts']))
            to_start -= len(hosts)
            self.log.info('Starting phase %d',phase)
            phase += 1
            success = run_parallel_bool(self._startHost, map(lambda x: (x,), hosts))
            if not success:
                self.log.error('Failed to start/install several hosts')
                return

        self.log.info('Setup started')
    
    def _buildHost(self,vm):
        if vm['status']['remote']:
            self.log.info(' Enable build for %s' %vm['name'])
            r = self.foreman.put('/api/hosts/%d' % vm['status']['remote']['id'],{'build':True})
            if r.status_code != 200:
                self.log.error('Failed to enable build for %s, server returned %d : %s',vm['name'],r.status_code,r.text)
    
    def enableBuild(self):
        self.log.info('Enable build for setup: %s',self.name)
        run_parallel(self._buildHost, map(lambda x: (x,), self.setup['hosts']))
        self.log.info('Build enabled')



