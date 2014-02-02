uberforeman
============================
uberforeman tends to be a simple command-line client for [foreman](http://theforeman.org) sitting on top of
[oVirt](http://ovirt.org) compute resource. Main goal of uberforeman is to manage multi-host setups and do 
simple orchrestration of deploying your hosts. With uberforeman, you can define kind of dependenies among your 
hosts, define provisioning order, so some hosts are installed earlier than others.

### Requirements
* **python2.7/3.3**
* **requests** - python http client library `easy_install requests`

If you do not have easy_install do `yum install python-setuptools`

### Installation
to install just for current user without root access, (you should include `~/.local/bin/` to your `$PATH`)

    python setup.py install --user

or run as root for system-wide install

    python setup.py install

### Getting started

#### 1. Create your ~/.uberforeman

You may need to save foreman connection info, credentials and your setup defaults before you start using 
uberforeman.

Create a file called `$HOME/.uberforeman` with following content

    [Login]
    username = foremanuser
    password = your pass # skip storing your password here and uberforeman will ask you
    [Foreman]
    url = https://foreman.yourdomain.org
    [Host Defaults]
    cluster = default #see sample


#### 2. Create your setup.json
Your setup JSON file, which describes VM setup you want to deploy and manage. See [sample](samples/main)
with comments (you can easily make it a valid JSON by `grep -v "#" samples/main > setup.json`).

To see status of your setup run 

    uberforeman setup.json --status

Initially, it will probably tell you to run `--install` first.

### Handling defaults

There are 3 levels of values (VM properties). Higher level has higher priority

 1. on user level in your `~/.uberforeman`
 2. on setup.json level - `default-host` key
 3. on VM level

You can run bellow command to print your setup.json file with applied defaults

    uberforeman setup.json --dump
 

### Important note

This project conatins some hardcoded pieces related to one particular datacenter I am using. Please do not
file issues or complain about it. Fixing the code and sending patches is much more appreciated.

