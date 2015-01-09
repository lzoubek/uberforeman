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

    def get(self,resource,headers={}):
        append = '?'
        if resource.find('?') > 0:
            append = '&'
        resource += append+'per_page=1000'
        headers['accept'] = 'version=2'
        return requests.get(self._url(resource),auth=self.auth,verify=False,headers=headers).json()

    def delete(self,resource):
        return requests.delete(self._url(resource),auth=self.auth,verify=False)

    def post(self,resource,data,headers={}):
        headers['Content-type'] = 'application/json'
        headers['accept'] = 'version=2'
        return requests.post(self._url(resource),json.dumps(data),auth=self.auth,verify=False,headers=headers)
    
    def put(self,resource,data,headers={}):
        headers['Content-type'] = 'application/json'
        headers['accept'] = 'version=2'
        return requests.put(self._url(resource),json.dumps(data),auth=self.auth,verify=False,headers=headers)
   
    def task(self,uuid, **kwargs):
        tasks = list(self.get('/api/orchestration/%s/tasks' % uuid)['results'])
        def f(obj):
            match = False
            for arg,value in kwargs.items():
                match |= obj[arg] == value
            return match

        return list(filter(f,tasks))

    def power(self,host,action='state'):
        return self.put('/api/hosts/%d/power' % host,{'power_action':action})

    def testConnection(self):
        test = self.get('/api')
        if 'message' in test.keys():
            raise Exception(test['message'])

    def hostgroups(self,**kwargs):
        if not hasattr(self,'host_groups'):
            self.host_groups = list(self.get('/api/hostgroups')['results'])

        def f(obj):
            match = False
            for arg,value in kwargs.items():
                match |= 'title' == arg and obj[arg].endswith(value)
                match |= obj[arg] == value
            return match
        
        return list(filter(f, self.host_groups))
    
    def computeResources(self,**kwargs):
        if not hasattr(self,'compute_resources'):
            self.compute_resources = list(self.get('/api/compute_resources')['results'])
        
        def f(obj):
            match = False
            for arg,value in kwargs.items():
                match |= obj[arg] == value
            return match

        return list(filter(f,self.compute_resources))

    def images(self, compute_resource, name):
        if not hasattr(self, 'disk_images'):
            self.disk_images  = list(self.get('api/compute_resources/%d/images' % compute_resource['id'])['results'])
       
        def f(obj):
            return obj['name'] == name

        return list(filter(f, self.disk_images))

    def domains(self,**kwargs):
        if not hasattr(self,'_domains'):
            self._domains = list(self.get('/api/domains')['results'])
        
        def f(obj):
            match = False
            for arg,value in kwargs.items():
                match |= obj[arg] == value
            return match
        
        return list(filter(f,self._domains))

    def hosts(self,**kwargs):
        if not hasattr(self,'_hosts'):
            self._hosts = list(self.get('/api/hosts')['results'])

        def f(obj):
            match = False
            for arg,value in kwargs.items():
                match |= obj[arg] == value
            return match

        hosts = list(filter(f,self._hosts))
        if len(hosts) == 1:
            return [self.get('/api/hosts/%d' % (hosts[0]['id']))]

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

