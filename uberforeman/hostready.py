"""This module contains various classes detecting state of host in sense of being installed.

"""
import sys, time, random
import requests
from requests.exceptions import ConnectionError,Timeout

# VM installation timeout in seconds
INSTALL_TIMEOUT=30*60 #30 minutes

class HostReady(object):

    def __init__(self,foreman):
        """Creates new instance

        :param foreman: ForemanClient instance
        """
        self.foreman = foreman

    """Base class"""
    def isInstalled(self,host):
        return False

    def getStatus(self,host):
        return 'N/A'

    def waitForInstalled(self,host,name):
        pass

class ImageBasedVMHostReady(HostReady):
    """
    This class detects host status based on orchestration uuid, so this implementation is host specific,
    thus host arguments are ignored
    """
    def __init__(self,foreman,task_uuid):
        self.foreman = foreman
        self.uuid = task_uuid
        self.tasks = None

    def isInstalled(self,host):
        return self.getStatus(host) == 'INSTALLED'

    def getStatus(self,host):
        try:
            self.tasks = self.foreman.task(self.uuid,status='running')
            if len(self.tasks) > 0:
                return self.tasks[0]['name']
            else:
                return 'INSTALLED'
        except:
            pass # not found?
            if self.tasks:
                return 'INSTALLED' # if we previously retrieved task and now the task does not exist anymore, we're done
            return 'N/A'
        return 'N/A'
    
    def waitForInstalled(self,host,name):
        t = 0
        t0 = int(time.time())
        while t < INSTALL_TIMEOUT:
            status = self.getStatus(host)
            if status.find('INSTALLED') == 0:
                print('VM Ready')
                return
            print('%s (%ds)' % (status,t))
            time.sleep(random.randint(1,5))
            now = int(time.time())
            t+= now - t0
            t0 = now
        raise Exception('VM installation reached timeout %ds, something is wrong' %  INSTALL_TIMEOUT)


class JonBCHostReady(HostReady):
    """
    This class is a simple checker for JON Bladecenter VMs status. It relies
    on http service running on port 49999 and exposing /tmp/ filesystem when VM runs
     in VM kickstarts there is a logic witch creates '.installing' when post-installation
     runs and removes it when it's done. There might also appear '.installation_error'
     which denotes installation failure
    """
    def isInstalled(self,host):
        return self.getStatus(host).find('INSTALLED') == 0

    def getStatus(self,host):
        status = 'http://%s:49999/.installing' % (host.rstrip('/'))
        try:
            r = requests.get(status,timeout=2)
            if r.status_code == 404:
                r = requests.get('http://%s:49999/.installation_error' % (host.rstrip('/')),timeout=2)
                if r.status_code == 200:
                    return 'INSTALLED FAILED : %s' % r.text
                return 'INSTALLED'
            elif r.status_code == 200:
                return 'INSTALLING'
        except Timeout:
            return 'N/A'
        except ConnectionError:
            return 'N/A'
    
    def waitForInstalled(self,host,name):
        t = 0
        t0 = int(time.time())
        while t < INSTALL_TIMEOUT:
            status = self.getStatus(host)
            if status.find('INSTALLED') == 0:
                print('\n%s is %s' % (name,status))
                return
            print('%s is %s (%ds)...' % (name,status,t))
            time.sleep(random.randint(1,5))
            now = int(time.time())
            t+= now - t0
            t0 = now
        raise Exception('VM installation reached timeout %ds, something is wrong' %  INSTALL_TIMEOUT)



