# Tinri VMware Snapshotting

The coldsnap Python tool is designed to shutdown a vm, snapshot it on a Tintri VMStore, and then power it back on.

## Sample Usage:

| option                       | description                                                 | type    |
| ---------------------------- | ----------------------------------------------------------- | ------- |
| -h, --help                   | show this help message and exit                             | flag    |
| --vcenter                    | vCenter to connect to                                       | string  |
| --vcenter_port               | vCenter Port to connect on                                  | int     |
| --vcenter_user               | Username to use for vCenter                                 | string  |
| --vcenter_password           | Password to use for vCenter                                 | string  |
| --vcenter_insecure           | disable ssl validation for vCenter                          | flag    |
| --tvmstore                   | Tintri Global Center to connect to                          | string  |
| --tvmstore_user              | Username to use for TGC                                     | string  |
| --tvmstore_password          | Password to use for TGC                                     | string  |
| --tvmstore_consistency_type  | The type of Tintri snapshot to take, defaults to "vm"       | string  |
| --tvmstore_snapshot_name     | A name for the snapshot                                     | string  |
| --tvmstore_snapshot_lifetime | minutes to keep snapshot , defaults to 1 month              | int     |
| --debug_mode                 | enable debug output                                         | flag    |
| --vms                        | the name of one or more vms to snapshot separated by spaces | strings |


```
$ read -s vcenter_pass
$ read -s tintri_pass
$ python coldsnap.py \
  --vcenter vcenter.example.com \
  --vcenter_user jdoe \
  --vcenter_password $vcenter_pass \
  --vcenter_insecure \
  --tvmstore array1.example.com \
  --tvmstore_user admin \
  --tvmstore_password $tintri_pass \
  --tvmstore_snapshot_name 'Sample snapshot' \
  --tvmstore_snapshot_lifetime 120 \
  --vms vm1.example.com vm2.example.com
```
