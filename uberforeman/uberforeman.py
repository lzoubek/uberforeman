#!/usr/bin/env python

__author__ = 'Libor Zoubek'
__email__ = 'lzoubek@redhat.com'

import sys,os, re
import argparse,json
try:
    import configparser
except:
    import ConfigParser as configparser

from controller import Uberforeman
from client import ForemanClient

def filterSetupJson(fd):
    """Filters out possible comments in setup JSON file"""
    return ''.join(list(filter(lambda line: re.search('^[ \t]*#',line) == None,fd.readlines())))

def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--status', action='store_true', help='Show status of your setup')
    group.add_argument('--install', action='store_true', help='Install setup')
    group.add_argument('--destroy', action='store_true', help='Destroy setup (delete all VMs)')
    group.add_argument('--reinstall', action='store_true', help='Rebuild setup (keep VMs but install again)')
    group.add_argument('--start', action='store_true', help='Start all VMs in setup (keep order)')
    group.add_argument('--stop', action='store_true', help='Stop all VMs in setup')
    group.add_argument('--restart', action='store_true', help='Restarts setup (same as --stop and --start)')
    group.add_argument('--force-install', action='store_true', help='Forces installation (same as --destroy and --install)')
    group.add_argument('--dump', action='store_true', help='Prints setup JSON file after applying all defaults')
    parser.add_argument('setup',help='Setup file')
    parser.add_argument('--user', help='Your foreman username',default=None)
    parser.add_argument('--password', help='Your foreman password',default=None)
    parser.add_argument('--foreman', help='Your foreman URL',default=None)
    args = parser.parse_args()
    foreman = user = passw = hostDefaults = None
    config = configparser.ConfigParser()
    try:
        config.read(os.path.join(os.environ['HOME'],'.uberforeman'))
        user = config.get('Login','username')
        passw = config.get('Login','password')
        foreman = config.get('Foreman','url')
        hostDefaults = dict(config.items('Host Defaults'))
    except:
        pass
    if args.user:
        user = args.user
    if args.password:
        passw = args.password
    if args.foreman:
        foreman = args.foreman
    if not user or not foreman:
        print('No user or foreman URL specified, use either --user or create $HOME/.uberforeman with following conent:\n[Login]\nusername=you\npassword=your\n[Foreman]\nurl=https://your.foreman\n[Host Defaults]\n#cluster=userspace')
        sys.exit(1)
    if not passw:
        import getpass
        passw = getpass.getpass()
    foreman = ForemanClient(foreman,user,passw)
    foreman.testConnection()
    with open(args.setup,'r') as setup:
        filtered = filterSetupJson(setup)
        fc = Uberforeman(foreman,json.loads(filtered),os.path.basename(args.setup),hostDefaults)
        fc.validateSetup()
        if args.dump:
            fc.dump()
        if args.status:
            fc.status()
        if args.install:
            fc.install()
        if args.stop:
            fc.stop()
        if args.start:
            fc.start()
        if args.restart:
            fc.stop()
            fc.start()
        if args.destroy:
            fc.destroy()
        if args.reinstall:
            fc.enableBuild()
            fc.stop()
            fc.start()
        if args.force_install:
            fc.destroy()
            fc.install()

if __name__ == '__main__':
    main()
