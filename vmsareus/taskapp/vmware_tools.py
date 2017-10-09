import atexit
import ssl

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
            settings.VCENTER_POD is None or
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

def clone_vm(template_name, vm_name):
        # content, template, vm_name, si,
        # datacenter_name, vm_folder, datastore_name,
        # cluster_name, resource_pool, power_on):

    si = connect()
    if si:
        atexit.register(Disconnect, si)
        content = si.RetrieveContent()

        folder = find_or_create_folder(content, settings.VCENTER_FOLDER)
        template = get_obj_in_folder(content, folder, [vim.VirtualMachine], template_name)
        resource_pool = get_obj(content, [vim.ResourcePool], settings.VCENTER_POOL)

        # for now you can use the same datastore as the template
        datastore = get_obj(content, [vim.Datastore], template.datastore[0].info.name)

        relospec = vim.vm.RelocateSpec(datastore=datastore, pool=resource_pool)
        clonespec = vim.vm.CloneSpec(location=relospec, powerOn=True)

        print ("cloning VM...")
        task = template.Clone(folder=folder, name=vm_name, spec=clonespec)
        tasks.wait_for_tasks(si, [task])
        print_result(task)

        if task.info.state != 'success':
            raise RuntimeError('failed during call to Clone')
    else:
        raise RuntimeError('Could not connect to vcenter using specified username and password')


def create_cluster_vm(template_name, vm_name):
    cpu_count = 3
    mem_gigs = 16
    si = connect()
    if si:
        atexit.register(Disconnect, si)
        content = si.RetrieveContent()

        folder = find_or_create_folder(content, settings.VCENTER_FOLDER)
        template = get_obj_in_folder(content, folder, [vim.VirtualMachine], template_name)
        pod = get_obj(content, [vim.StoragePod], settings.VCENTER_POD)
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
    si = connect()

    if si:
        atexit.register(Disconnect, si)
        content = si.RetrieveContent()
        folder = find_or_create_folder(content, settings.VCENTER_FOLDER)
        vm = get_obj_in_folder(content, folder, [vim.VirtualMachine], vm_name)
        if vm:
            all_ips = [ip.ipAddress for nic in vm.guest.net for ip in nic.ipConfig.ipAddress if ip.state == 'preferred']
            # ip = [ip.ipAddress for nic in guest.net if nic.ipConfig is not None for ip in nic.ipConfig.ipAddress if ip.state == 'preferred']
            ip_4s = [item for item in all_ips if '.' in item]

            return {'os': vm.summary.config.guestFullName,
                    'power': vm.summary.runtime.powerState,
                    'ip': ip_4s[0] if ip_4s else None}
        else:
            raise RuntimeError("could not find vm " + vm_name)
    else:
        raise RuntimeError('Could not connect to vcenter using specified username and password')




def copy_disk(src_url, dst_url):
    si = connect()

    if si:
        atexit.register(Disconnect, si)
        vdm = si.RetrieveContent().virtualDiskManager
        task = vdm.CopyVirtualDisk(src_url, None, dst_url, None, None, False)
        tasks.wait_for_tasks(si, [task])
        if task.info.state != 'success':
            raise RuntimeError('failed during call to CopyDisk')
        else:
            print('drive copy complete result: %s' % task.info.result)
    else:
        raise RuntimeError('Could not connect to vcenter using specified username and password')


def make_dir_if_not_present(target_dir_url):
    si = connect()

    if si:
        atexit.register(Disconnect, si)
        fm = si.RetrieveContent().fileManager
        print(target_dir_url)
        fm.MakeDirectory(target_dir_url)
    else:
        raise RuntimeError('Could not connect to vcenter using specified username and password')


def delete_disk(target_url):
    si = connect()

    if si:
        atexit.register(Disconnect, si)
        content = si.RetrieveContent()
        vdm = content.virtualDiskManager
        task = vdm.DeleteVirtualDisk(target_url, None)
        tasks.wait_for_tasks(si, [task])
        if task.info.state != 'success':
            raise RuntimeError('failed during call to DeleteDisk')
        else:
            print('Disk delete finished with result: %s' % task.info.result)
    else:
        raise RuntimeError('Could not connect to vcenter using specified username and password')


def attach_drive(vm_name, drive_name):
    si = connect()

    if si:
        atexit.register(Disconnect, si)
        content = si.RetrieveContent()
        folder = find_or_create_folder(content, settings.VCENTER_FOLDER)
        vm = get_obj_in_folder(content, folder, [vim.VirtualMachine], vm_name)
        if vm:
            unit_number = 0
            for dev in vm.config.hardware.device:
                if hasattr(dev.backing, 'fileName'):
                    unit_number = max(unit_number, int(dev.unitNumber) + 1)
                    # unit_number 7 reserved for scsi controller
                    if unit_number == 7:
                        unit_number += 1
                    if unit_number >= 16:
                        raise RuntimeError("we don't support this many disks")
                if isinstance(dev, vim.vm.device.VirtualSCSIController):
                    controller = dev

            disk_spec = vim.vm.device.VirtualDeviceSpec()
            disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
            disk_spec.device = vim.vm.device.VirtualDisk()
            disk_spec.device.unitNumber = unit_number
            disk_spec.device.controllerKey = controller.key

            backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
            backing.fileName = drive_name
            backing.diskMode = 'persistent'
            disk_spec.device.backing = backing

            spec = vim.vm.ConfigSpec()
            spec.deviceChange = [disk_spec]

            task = vm.ReconfigVM_Task(spec=spec)
            tasks.wait_for_tasks(si, [task])
            if task.info.state != 'success':
                raise RuntimeError('failed during connection of drive to vm.')
            else:
                print('Disk attach finished with result: %s' % task.info.result)
        else:
            raise RuntimeError("could not find vm " + vm_name)
    else:
        raise RuntimeError('Could not connect to vcenter using specified username and password')
