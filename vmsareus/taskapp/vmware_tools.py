import atexit
import math
import ssl
import time
from datetime import datetime

import os
from django.conf import settings
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
from .tools import tasks

if not settings.configured:
    # set the default Django settings module for the 'celery' program.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')  # pragma: no cover

class ConfigException(Exception):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)

def validate_config():
    if (settings.VCENTER_FOLDER is None or
            settings.VCENTER_DATASTORE is None or
            settings.VCENTER_CLUSTER is None or
            settings.VCENTER_HOST is None or
            settings.VCENTER_USER is None or
            settings.VCENTER_PASSWORD is None or
            settings.VCENTER_PORT is None or
            settings.VCENTER_DATACENTER is None):
        raise ConfigException('Configuration of required VCENTER value missing')


def connect():
    context = ssl._create_unverified_context()
    si = SmartConnect(host=settings.VCENTER_HOST,
                      user=settings.VCENTER_USER,
                      pwd=settings.VCENTER_PASSWORD,
                      port=int(settings.VCENTER_PORT),
                      sslContext=context)
    return si


def get_obj_in_folder(content, folder, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView(
        folder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def get_obj(content, vimtype, name):
    return get_obj_in_folder(content, content.rootFolder, vimtype, name)


def find_or_create_folder(content, foldername):
    dc = get_obj(content, [vim.Datacenter], settings.VCENTER_DATACENTER)
    if dc:
        return (get_obj(content, [vim.Folder], foldername) or
                dc.vmFolder.CreateFolder(foldername) or
                None)
    else:
        print("could not locate specified datacenter.")
        return None


def delete_if_exists(vm_name):
    validate_config()

    si = connect()

    if si:
        #print("connection made to vcenter")
        atexit.register(Disconnect, si)
        content = si.RetrieveContent()

        vm = get_obj(content, [vim.VirtualMachine], vm_name)
        if vm:
            print("Found Delete Candidate: {0}".format(vm.name))
            print("The current powerState is: {0}".format(vm.runtime.powerState))
            if format(vm.runtime.powerState) == "poweredOn":
                print("Attempting to power off {0}".format(vm.name))
                task = vm.PowerOffVM_Task()
                tasks.wait_for_tasks(si, [task])
                print("{0}".format(task.info.state))
            print("Destroying VM {0}".format(vm.name))
            task = vm.Destroy_Task()
            tasks.wait_for_tasks(si, [task])
        else:
            print("could not locate VM named: " + vm_name)


def getsummary(result):
    if hasattr(result, 'summary'):
        return result.summary
    elif hasattr(result, 'vm'):
        return result.vm.summary
    else:
        return None


def print_result(task):
    #print(task.info.state)
    #print(task.info.key)
    print(task.info.descriptionId)
    #if isinstance(task.info.reason, vim.TaskReasonUser):
    #    print(task.info.reason.userName)

    summary = getsummary(task.info.result)
    print("Name       : ", summary.config.name)
    print("Path       : ", summary.config.vmPathName)
    print("Guest      : ", summary.config.guestFullName)
    print("State      : ", summary.runtime.powerState)
    if summary.guest is not None:
        ip = summary.guest.ipAddress
        if ip:
            print("IP         : ", ip)


def create_cluster_vm(template_name, vm_name):
    cpu_count = 3
    mem_gigs = 16
    validate_config()
    si = connect()
    if si:
        atexit.register(Disconnect, si)
        content = si.RetrieveContent()

        template = get_obj(content, [vim.VirtualMachine], template_name)
        pod = get_obj(content, [vim.StoragePod], settings.VCENTER_DATASTORE)
        folder = find_or_create_folder(content, settings.VCENTER_FOLDER)
        resource_pool = get_obj(content, [vim.ResourcePool], settings.VCENTER_POOL)

        cloneSpec = vim.vm.CloneSpec()
        cloneSpec.powerOn = True

        cloneSpec.config = vim.vm.ConfigSpec()
        cloneSpec.config.name = vm_name
        cloneSpec.config.numCPUs = cpu_count
        cloneSpec.config.memoryMB = mem_gigs * 1024

        cloneSpec.location = vim.vm.RelocateSpec()
        cloneSpec.location.pool = resource_pool

        storagespec = vim.storageDrs.StoragePlacementSpec()
        storagespec.vm = template
        storagespec.type = 'clone'
        storagespec.folder = folder
        storagespec.cloneSpec = cloneSpec
        storagespec.cloneName = vm_name
        storagespec.podSelectionSpec = vim.storageDrs.PodSelectionSpec()
        storagespec.podSelectionSpec.storagePod = pod

        rec = content.storageResourceManager.RecommendDatastores(storageSpec=storagespec)
        rec_key = rec.recommendations[0].key

        task = content.storageResourceManager.ApplyStorageDrsRecommendation_Task(rec_key)

        print("starting Apply")
        tasks.wait_for_tasks(si, [task])

        print_result(task)

        if task.info.state != 'success':
            raise RuntimeError('failed during call to ApplyStorageDrsRecommendation_Task')
    else:
        raise RuntimeError('Could not connect to vcenter using specified username and password')


def get_vm_info(vm_name):
    validate_config()
    si = connect()

    if si:
        atexit.register(Disconnect, si)
        content = si.RetrieveContent()
        folder = find_or_create_folder(content, settings.VCENTER_FOLDER)
        vm = get_obj_in_folder(content, folder, [vim.VirtualMachine], vm_name)
        if vm:
            if vm.summary.guest is not None:
                ip = vm.summary.guest.ipAddress
            else:
                ip = 'not assigned'

            return {'os': vm.summary.config.guestFullName,
                    'power': vm.summary.runtime.powerState,
                    'ip': ip}
        else:
            raise RuntimeError("could not find vm " + vm_name)
    else:
        raise RuntimeError('Could not connect to vcenter using specified username and password')


