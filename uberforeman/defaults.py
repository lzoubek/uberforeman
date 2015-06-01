
# defaults for VM definition in setup
VM_DEFAULT = {
        "computeResource":"rhevm",
        "clones":0,
        "cluster":"userspace",
        "storage":"BC_shared",
        "domain":"bc.jonqe.lab.eng.bos.redhat.com",
        "arch":"x86_64",
        "disk":10,
        "ram":4,
        "cpus":1,
        "image":""
        }

# defaults for foreman VM representation
FOREMAN_DEFAULT = {
        "name" : "simple-host1",
        "environment_id" : "1",
        "architecture_id" : "1",
        "operatingsystem_id" : "11",
        "domain_id" : "1",
        "puppet_proxy_id" : "1",
        "compute_resource_id" : "2",
        "hostgroup_id" : "-1",
        "provision_method" : "build",
        "build" : "1",
        "ptable_id" : "1",
        "image_id" : None,
        "host_parameters_attributes":{},
        "compute_attributes" : {
            "cores" : "1",
            "cluster" : "fcb97476-3365-11e2-94d7-5254009cc188",
            "memory" : "4294967296",
            "template" : "00000000-0000-0000-0000-000000000000",
            "start" : "0",
            "interfaces_attributes" : {
                "new_1363158080936" : {
                    "network" :
                    "00000000-0000-0000-0000-000000000009",
                    "name" : "eth0",
                    "_delete" : ""
                    }
            },
            "volumes_attributes" : {
                "0" : {
                    "size_gb" : "15",
                    "storage_domain" : "b250d85c-2837-4efa-8c94-0f7c262418cc",
                    "_delete" : "",
                    "id" : ""
                    }
                }
            }
        }


