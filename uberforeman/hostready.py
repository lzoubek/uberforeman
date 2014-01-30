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
            sys.stdout.write('%s is %s (%ds)...\r' % (name,status,t))
            sys.stdout.flush()
            time.sleep(random.randint(1,5))
            now = int(time.time())
            t+= now - t0
            t0 = now
        raise Exception('VM installation reached timeout %ds, something is wrong' %  INSTALL_TIMEOUT)



