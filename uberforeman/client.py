import requests, json

def getOrFail(f):
    def wrap(*args,**kwargs):
        res = f(*args,**kwargs)
        if res:
            if len(res) == 1:
                return res[0]
        raise Exception('Unable to find %s by criteria %s' % (f.__name__,str(kwargs)))
    return wrap

def getOrNone(f):
    def wrap(*args,**kwargs):
        res = f(*args,**kwargs)
        if res:
            if len(res) == 1:
                return res[0]
    return wrap

class ForemanClient(object):

    def __init__(self,url,user,passw):
        self.auth = (user,passw)
        self.url = url.rstrip('/')

    def _url(self,url):
        if url.find('http') == 0:
            return url
        return self.url+'/'+url.lstrip('./')

    def get(self,resource):
        append = '?'
        if resource.find('?') > 0:
            append = '&'
        resource += append+'per_page=1000'
        return requests.get(self._url(resource),auth=self.auth,verify=False).json()

    def delete(self,resource):
        return requests.delete(self._url(resource),auth=self.auth,verify=False)

    def post(self,resource,data,headers={}):
        headers['Content-type'] = 'application/json'
        return requests.post(self._url(resource),json.dumps(data),auth=self.auth,verify=False,headers=headers)
    
    def put(self,resource,data,headers={}):
        headers['Content-type'] = 'application/json'
        return requests.put(self._url(resource),json.dumps(data),auth=self.auth,verify=False,headers=headers)
    
    def power(self,host,action='state'):
        return self.put('/api/hosts/%d/power' % host,{'power_action':action},headers={'accept':'version=2'})

    def testConnection(self):
        test = self.get('/api')
        if 'message' in test.keys():
            raise Exception(test['message'])

    def hostgroups(self,**kwargs):
        if not hasattr(self,'host_groups'):
            self._host_groups_label_map = {}
            def f(hg):
                self._host_groups_label_map[str(hg['hostgroup']['id'])] = hg['hostgroup']['name']
                return hg['hostgroup']

            self.host_groups = list(map(f,self.get('/api/hostgroups')))
            # build label field containing whole hostgroup name including ancestry names
            for hg in self.host_groups:
                hg['label'] = hg['name']
                if hg['ancestry']:
                    hg['label'] = '/'.join(map(lambda id:self._host_groups_label_map[id],hg['ancestry'].split('/')))
                    hg['label']+= '/' + hg['name']

        def f(obj):
            match = False
            for arg,value in kwargs.items():
                match |= 'label' == arg and obj[arg].endswith(value)
                match |= obj[arg] == value
            return match

        return list(filter(f, self.host_groups))
    
    def computeResources(self,**kwargs):
        if not hasattr(self,'compute_resources'):
            self.compute_resources = list(map(lambda x: x['compute_resource'],self.get('/api/compute_resources')))
        
        def f(obj):
            match = False
            for arg,value in kwargs.items():
                match |= obj[arg] == value
            return match

        return list(filter(f,self.compute_resources))

    def domains(self,**kwargs):
        if not hasattr(self,'_domains'):
            self._domains = list(map(lambda x: x['domain'],self.get('/api/domains')))
        
        def f(obj):
            match = False
            for arg,value in kwargs.items():
                match |= obj[arg] == value
            return match
        
        return list(filter(f,self._domains))

    def hosts(self,**kwargs):
        if not hasattr(self,'_hosts'):
            self._hosts = list(map(lambda x: x['host'],self.get('/api/hosts')))

        def f(obj):
            match = False
            for arg,value in kwargs.items():
                match |= obj[arg] == value
            return match

        hosts = list(filter(f,self._hosts))
        if len(hosts) == 1:
            return [self.get('/api/hosts/%d' % (hosts[0]['id']))['host']]

class OvirtClient(object):

    @classmethod
    def fromComputeResource(cls,computeResource):
        return cls(computeResource['url'],computeResource['user'],'todo...')

    def __init__(self,url,user,passw):
        self.auth = (user,passw)
        self.url = url.rstrip('/')
    
    def storages(self,**kwargs):
        domains = {
                "BC_shared":{"id":"b250d85c-2837-4efa-8c94-0f7c262418cc"},
                "BC_perf":{"id":"05cd6fd4-de9a-4e9c-9a92-925b3e263b33"},
            }
        if kwargs['name'] in domains.keys():
            return [domains[kwargs['name']]]
    
    def clusters(self,**kwargs):
        clusters = {
                "userspace":{"id":"fcb97476-3365-11e2-94d7-5254009cc188"},
                "automation":{"id":"99408929-82cf-4dc7-a532-9d998063fa95"},
                "performance":{"id":"93a8fc6e-3e36-11e2-8760-5254009cc188"}
        }
        if kwargs['name'] in clusters.keys():
            return [clusters[kwargs['name']]]

