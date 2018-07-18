#! /usr/bin/python

import argparse, yaml, xlrd, socket, sys
import os
import mysql.connector
import ruamel
from ruamel.yaml import YAML
import prlsdkapi

consts = prlsdkapi.prlsdk.consts
#-------------------------------------------------------------------------------------------------------------------------------------------
parser = argparse.ArgumentParser(usage="The utility reads from XLS names and description of VM and get from MariaDB name of its host.\n\rBefore using the utility, first configure the configuration YAML file ./xls-db_conf.yaml\n\r\n\rFIRST - run with key -get - utility reads from XLS VMs and description; then reads from MariaDB VM Hosts and write hosts.yaml (this file needs for -set key).\n\rSECOND - to set description to R-Management Console you must set the credentials in the file hosts.yaml and run the utility with key -set\n\rAlso the utility does a backup of the VM description to a file backup_description.yaml", formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("-get", "--get_description", action="store_true", help="get description from XLS")
parser.add_argument("-set", "--set_description", action="store_true", help="set description to R-Management Console")

if len(sys.argv)==1:
    parser.print_help(sys.stderr)
    sys.exit(1)
#-------------------------------------------------------------------------------------------------------------------------------------------
#read config from yaml file
config_file=open("./xls-db_conf.yaml")
cfg = yaml.load(config_file)

XLS_FILE = (cfg['XLS_FILE'])
ENCODE = (cfg['ENCODE'])
HOST_REPRESENT = (cfg['HOST_REPRESENT'])
VM_NAME_SHEET = int((cfg['VM_NAME_SHEET']))
VM_NAME_COLUMN = int((cfg['VM_NAME_COLUMN']))
VM_DESCRIPTION_SHEET = int((cfg['VM_DESCRIPTION_SHEET']))
VM_DESCRIPTION_COLUMN = int((cfg['VM_DESCRIPTION_COLUMN']))

MARIADB_USER = (cfg['MARIADB_USER'])


#-------------------------------------------------------------------------------------------------------------------------------------------
def parse_xls(XLS_FILE,VM_NAME_SHEET,VM_NAME_COLUMN,VM_DESCRIPTION_SHEET,VM_DESCRIPTION_COLUMN,ENCODE,HOST_REPRESENT):

#get VM and description from XLS
    tbl = []
    book = xlrd.open_workbook(XLS_FILE)
    vm_sheet = book.sheet_by_index(VM_NAME_SHEET)#Switching to sheet
    for rownum in range(vm_sheet.nrows)[1:]:#[1:] - is skipping first title row
        row = vm_sheet.row_values(rownum)
#        print row[1]
        tbl.append(row[VM_NAME_COLUMN])
    for j in range(len(tbl)):
        vm_description_sheet=book.sheet_by_index(VM_DESCRIPTION_SHEET)
        row = vm_description_sheet.row_values(j+1)#(j+1) - is skipping first title row
        tbl[j]=tbl[j],row[VM_DESCRIPTION_COLUMN]
#---------------------------------------------------------------------------------------------------------------
#get info from MariaDB
    mariadb_connection = mysql.connector.connect(user='USERNAME', database='DBNAME')
    cursor = mariadb_connection .cursor()
    if HOST_REPRESENT == "hostname":
        query = ("select name, parent_title from vEnvironments where parent_title!='None'")
    if HOST_REPRESENT == "ip":
        query = ("select E.name, H.ip_address from vEnvironments E inner join vHosts H on E.parent_title = H.hostname")
    cursor.execute(query)
    dbresult = cursor.fetchall()

    cursor.close()
    mariadb_connection.close()
#---------------------------------------------------------------------------------------------------------------
#convert tuple of tuples to list of lists
    dbresult=list(list(x) for x in dbresult)
#decode every element to "utf-8"
    for i in range(len(dbresult)):
        dbresult[i][0]=dbresult[i][0].decode(ENCODE)
        dbresult[i][1]=dbresult[i][1].decode(ENCODE)
#---------------------------------------------------------------------------------------------------------------
#heap - is array VM, host, description
    heap = []
    for j in range(len(tbl)):
        for i in range(len(dbresult)):
            if tbl[j][0] == dbresult[i][0]:
                heap.append((tbl[j][0], dbresult[i][1], tbl[j][1]))
                break                
            if i == (len(dbresult)-1):
                heap.append((tbl[j][0], "NULL", tbl[j][1]))
#---------------------------------------------------------------------------------------------------------------
#get longest length of VM column (need for formatting output)    
    longest_first=0
    for j in range(len(heap)):
        if len(heap[j][0]) > longest_first:
            longest_first=len(heap[j][0])
    
#get longest lengtn of host column (need for formatting output)
    longest_second=0
    for j in range(len(heap)):
        if len(heap[j][1]) > longest_second:
            longest_second=len(heap[j][1])
    
#print VM (from XLS), host (from MariaDB; if hos not found - then print 'NULL'), description (from XLS)
    print "This table shows VMs, hosts and description. If the host is shown as NULL, then for this VM we can not change the description."
    for j in range(len(heap)):
        if heap[j][1] == "NULL":
            print "{0:{1}} {2} {3}".format(heap[j][0],longest_first,("\x1b[0;32;41m"+"NULL"+(" "*(longest_second-4))+"\x1b[0;32;40m"),heap[j][2].encode(ENCODE))
        else:
            print "{0:{1}} {2:{3}} {4}".format(heap[j][0],longest_first,heap[j][1],longest_second,heap[j][2].encode(ENCODE))
#---------------------------------------------------------------------------------------------------------------
#get unique hosts from heap (for which we need passwords)
    hosts = []
    for j in range(len(heap)):
        if heap[j][1] == "NULL":
            continue 
        if heap[j][1] not in hosts:
            hosts.append(heap[j][1])     

    hosts=sorted(hosts)#sort hosts alpabetically    

#print hosts
    print "For these hosts you need to specify the credentials in the configuration file hosts.yaml"
    for j in hosts:
        print j
#---------------------------------------------------------------------------------------------------------------
#write config for hosts: hosts.yaml		
    config_file=open("./hosts.yaml", 'w')		
	
    yaml = YAML()
    yaml.explicit_start = True
    yaml.Loader=ruamel.yaml.RoundTripLoader
    yaml.Dumper=ruamel.yaml.RoundTripDumper

    for j in hosts:
        yaml_str="HOST: "+j+"\nUSER: USERNAME\nPASSWORD: \n"
        data = yaml.load(yaml_str)
        yaml.dump(data, config_file)
    config_file.close()
#---------------------------------------------------------------------------------------------------------------
#write heap to heap.yaml (for using in key -set)
    config_file=open("./heap.yaml", 'w')		
	
    yaml = YAML()
    yaml.explicit_start = True
    yaml.Loader=ruamel.yaml.RoundTripLoader
    yaml.Dumper=ruamel.yaml.RoundTripDumper

    for j in range(len(heap)):
        if heap[j][1] == "NULL":
            continue
        yaml_str="VM: "+heap[j][0]+"\nHOST: "+heap[j][1]+"\nDESC: "+heap[j][2]+"\n"
        data = yaml.load(yaml_str)
        yaml.dump(data, config_file)
    config_file.close()
#---------------------------------------------------------------------------------------------------------------  
    return heap
#-------------------------------------------------------------------------------------------------------------------------------------------
def backup_description():

    heap_file=open("./heap.yaml")
    hosts_file=open("./hosts.yaml")
    heap_cfg = list(yaml.load_all(heap_file))
    hosts_cfg = list(yaml.load_all(hosts_file))

    backup_file=open("./backup_description.yaml", 'w')

    yml = YAML()
    yml.explicit_start = True
    yml.Loader=ruamel.yaml.RoundTripLoader
    yml.Dumper=ruamel.yaml.RoundTripDumper

    for j in heap_cfg:
        for i in hosts_cfg:
            if j['HOST'] == i['HOST']:
#                print j['HOST'],i['USER'],i['PASSWORD'],j['VM'],api_get_vm_desc(j['HOST'],i['USER'],i['PASSWORD'],j['VM'])
                yaml_str="VM: "+j['VM']+"\nHOST: "+j['HOST']+"\nDESC: "+api_get_vm_desc(j['HOST'],i['USER'],i['PASSWORD'],j['VM'])+"\n"
                data = yml.load(yaml_str)
                yml.dump(data, backup_file)
                break

    heap_file.close()
    hosts_file.close()
    backup_file.close()      
#-------------------------------------------------------------------------------------------------------------------------------------------
def api_get_vm_desc(HOST,USER,PASSW,VM):
    prlsdkapi.init_server_sdk()

    server = prlsdkapi.Server()

    server.login(HOST,USER,PASSW, '', 0, 0, consts.PSL_NORMAL_SECURITY).wait()

    vm = api_get_vm(server,VM)

    vm_config = vm.get_config()

    st=str(vm_config.get_description())

    server.logoff()
    prlsdkapi.deinit_sdk()

    return st
#-------------------------------------------------------------------------------------------------------------------------------------------
def api_get_vm(server,vm_name):
    result = server.get_vm_list().wait()
# Iterate through all VMs until we find the one we're looking for
    for i in range(result.get_params_count()):
        vm = result.get_param_by_index(i)
        name = vm.get_name()
        if name.startswith(vm_name):
            return vm
#-------------------------------------------------------------------------------------------------------------------------------------------
def api_vm_change_description(HOST,USER,PASSW,VM,DESCRIPTION):
    prlsdkapi.init_server_sdk()

    server = prlsdkapi.Server()
   
    server.login(HOST,USER,PASSW, '', 0, 0, consts.PSL_NORMAL_SECURITY).wait()

    vm = api_get_vm(server,VM)

    vm.begin_edit().wait()

    vm.set_description(DESCRIPTION.encode("utf_8"))

    vm.commit().wait()

    server.logoff()
    prlsdkapi.deinit_sdk()
#-------------------------------------------------------------------------------------------------------------------------------------------
def set_desc():
    backup_description()
    heap_file=open("./heap.yaml")
    hosts_file=open("./hosts.yaml")
    heap_cfg = list(yaml.load_all(heap_file))
    hosts_cfg = list(yaml.load_all(hosts_file))

    for j in heap_cfg:
        for i in hosts_cfg:
            if j['HOST'] == i['HOST']:
                if j['DESC'] == None:
                    j['DESC'] = ""
                api_vm_change_description(j['HOST'],i['USER'],i['PASSWORD'],j['VM'],j['DESC'])
                print "For VM",j['VM'],"setting description",j['DESC'].encode("utf_8"),"OK"
                break
    heap_file.close()
    hosts_file.close()
#-------------------------------------------------------------------------------------------------------------------------------------------
def main():
    args = parser.parse_args()
    if args.get_description:
        parse_xls(XLS_FILE,VM_NAME_SHEET,VM_NAME_COLUMN,VM_DESCRIPTION_SHEET,VM_DESCRIPTION_COLUMN,ENCODE,HOST_REPRESENT)
    if args.set_description:
        if os.path.exists("./hosts.yaml") and os.path.exists("./heap.yaml"):
            set_desc()
        else:
            print "First run utility with key -get and it is write two files: ./heap.yaml (with VMs, hosts and description) and ./hosts.yaml (with credentials to hosts)"
            sys.exit(1)
#-------------------------------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
