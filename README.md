# Set-VM-description-from-XLS-file-using-Parallels-API
The utility reads from XLS names and description of VM and get from MariaDB name of its host.<br/>
Before using the utility, first configure the configuration YAML file ./xls-db_conf.yaml<br/>
FIRST - run with key -get - utility reads from XLS VMs and description; then reads from MariaDB VM Hosts and write hosts.yaml (this file needs for -set key).<br/>
SECOND - to change description for VM you must set the credentials in the file hosts.yaml and run the utility with key -set<br/>
Also the utility does a backup of the VM description to a file backup_description.yaml<br/>
