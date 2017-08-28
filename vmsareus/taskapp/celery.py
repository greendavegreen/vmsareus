from __future__ import absolute_import

import atexit
import math
import os
import ssl
import time

from celery import Celery
from django.apps import apps, AppConfig
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

from .tools import tasks

if not settings.configured:
    # set the default Django settings module for the 'celery' program.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')  # pragma: no cover

app = Celery('vmsareus')

class CeleryConfig(AppConfig):
    name = 'vmsareus.taskapp'
    verbose_name = 'Celery Config'

    def ready(self):
        # Using a string here means the worker will not have to
        # pickle the object when using Windows.
        app.config_from_object('django.conf:settings')
        installed_apps = [app_config.name for app_config in apps.get_app_configs()]
        app.autodiscover_tasks(lambda: installed_apps, force=True)

        if hasattr(settings, 'RAVEN_CONFIG'):
            # Celery signal registration

            from raven import Client as RavenClient
            from raven.contrib.celery import register_signal as raven_register_signal
            from raven.contrib.celery import register_logger_signal as raven_register_logger_signal

            raven_client = RavenClient(dsn=settings.RAVEN_CONFIG['DSN'])
            raven_register_logger_signal(raven_client)
            raven_register_signal(raven_client)




@app.task(bind=True)
def debug_task(self):
    from ..vmleases.models import Vm

    print('Request: {0!r}'.format(self.request))  # pragma: no cover



def validate_config():
    return not (settings.VCENTER_FOLDER is None or
                settings.VCENTER_DATASTORE is None or
                settings.VCENTER_CLUSTER is None or
                settings.VCENTER_HOST is None or
                settings.VCENTER_USER is None or
                settings.VCENTER_PASSWORD is None or
                settings.VCENTER_PORT is None or
                settings.VCENTER_DATACENTER is None)

def connect():
    context = ssl._create_unverified_context()
    si = SmartConnect(host=settings.VCENTER_HOST,
                      user=settings.VCENTER_USER,
                      pwd=settings.VCENTER_PASSWORD,
                      port=int(settings.VCENTER_PORT),
                      sslContext=context)
    return si

def get_obj(content, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj

def find_or_create_folder(content, foldername):
    dc = get_obj(content, [vim.Datacenter], settings.VCENTER_DATACENTER)
    if dc:
        return (get_obj(content, [vim.Folder], foldername) or
                dc.vmFolder.CreateFolder(foldername) or
                None)
    else:
        print("could not locate specified datacenter.")
        return None

@app.task
def update_vm_state(pk):
    from ..vmleases.models import Vm
    try:
        obj = Vm.objects.get(pk=pk)
        print(obj.vm_state)
        obj.vm_state = 'r'
        obj.save()
        print(obj.vm_state)
    except ObjectDoesNotExist:
        print('VM does not exist: {0!s}'.format(pk))


@app.task
def confirm_folder():
    if validate_config():
        print("valid config")
    else:
        print("invalid config")

    si = connect()

    if si:
        print("connection made to vcenter")
        atexit.register(Disconnect, si)
        content = si.RetrieveContent()
        folder = find_or_create_folder(content, settings.VCENTER_FOLDER)
        if folder:
            print("folder now exists")
        else:
            print("error locating or creating folder")


@app.task
def fill_lease(id):
    from ..vmleases.models import Vm
    try:
        time.sleep(5)
        obj = Vm.objects.get(pk=id)

        if validate_config():
            obj.vm_state = 'c'
            obj.save()

            name = 'dev-vm-{}-{}'.format(obj.author.username, int(time.time()))
            if create_vm('ubuminitemplate.v1', 1, 4, name):
                obj.vm_state = 'r'
                obj.vm_name = name
                obj.save()
                print('VM created:{} status {}'.format(name, obj.vm_state))
            else:
                print('call to vm creation failed')
                obj.vm_state = 'a'
                obj.save()
        else:
            print("invalid config")
            obj.vm_state = 'a'
            obj.save()
    except ObjectDoesNotExist:
        print('VM does not exist: {0!s}'.format(id))
    pass


@app.task
def create_vm(template_name, cpu_count, mem_gigs, vm_name):
    if validate_config():
        si = connect()
        if si:
            # print("connection made to vcenter")
            atexit.register(Disconnect, si)
            content = si.RetrieveContent()

            datastore = get_obj(content, [vim.Datastore], settings.VCENTER_DATASTORE)
            folder = find_or_create_folder(content, settings.VCENTER_FOLDER)
            cluster = get_obj(content, [vim.ClusterComputeResource], settings.VCENTER_CLUSTER)

            # resource pools are optional
            if settings.VCENTER_POOL:
                resource_pool = get_obj(content, [vim.ResourcePool], settings.VCENTER_POOL)
            else:
                resource_pool = cluster.resourcePool

            template = get_obj(content, [vim.VirtualMachine], template_name)

            clonespec = vim.vm.CloneSpec()
            clonespec.powerOn = True

            relospec = vim.vm.RelocateSpec()
            relospec.datastore = datastore
            relospec.pool = resource_pool
            clonespec.location = relospec

            config = vim.vm.ConfigSpec()
            config.numCPUs = cpu_count
            config.memoryMB = mem_gigs * 1024
            config.name = vm_name
            clonespec.config = config

            # print("cloning VM...")
            task = template.Clone(folder=folder, name=vm_name, spec=clonespec)
            # print("clone call returned, now waiting for task to complete.")

            tasks.wait_for_tasks(si, [task])
            # print("Clone Complete.")

            result = (task.info.state == 'success')
            print_result(task)
            return result
    else:
        print("Could not connect to the specified host using specified "
              "username and password")

    return False


def print_result(task):
    print(task.info.state)
    print(task.info.key)
    print(task.info.descriptionId)
    if isinstance(task.info.reason, vim.TaskReasonUser):
        print(task.info.reason.userName)
    summary = task.info.result.summary
    print("Name       : ", summary.config.name)
    print("Path       : ", summary.config.vmPathName)
    print("Guest      : ", summary.config.guestFullName)
    print("State      : ", summary.runtime.powerState)
    if summary.guest is not None:
        ip = summary.guest.ipAddress
        if ip:
            print("IP         : ", ip)


@app.task
def delete_vm(vm_name):
    if validate_config():
        print("valid config")
    else:
        print("invalid config")
        return

    si = connect()

    if si:
        print("connection made to vcenter")
        atexit.register(Disconnect, si)
        content = si.RetrieveContent()

        vm = get_obj(content, [vim.VirtualMachine], vm_name)
        if vm:
            print("Found: {0}".format(vm.name))
            print("The current powerState is: {0}".format(vm.runtime.powerState))
            if format(vm.runtime.powerState) == "poweredOn":
                print("Attempting to power off {0}".format(vm.name))
                task = vm.PowerOffVM_Task()
                tasks.wait_for_tasks(si, [task])
                print("{0}".format(task.info.state))

            print("Destroying VM from vSphere.")
            task = vm.Destroy_Task()
            tasks.wait_for_tasks(si, [task])
            print("Done.")
        else:
            print("could not locate VM named: " + vm_name)

@app.task
def get_vm_info(vm_name):
    if validate_config():
        print("valid config")
    else:
        print("invalid config")
        return None

    si = connect()

    if si:
        print("connection made to vcenter")
        atexit.register(Disconnect, si)
        content = si.RetrieveContent()

        vm = get_obj(content, [vim.VirtualMachine], vm_name)
        if vm:
            return {'os': vm.summary.config.guestFullName,
                    'power': vm.summary.runtime.powerState}

    return None

@app.task
def get_ip(vm_name):
    if validate_config():
        print("valid config")
    else:
        print("invalid config")
        return None

    si = connect()

    if si:
        print("connection made to vcenter")
        atexit.register(Disconnect, si)
        content = si.RetrieveContent()

        vm = get_obj(content, [vim.VirtualMachine], vm_name)
        if vm:
            if vm.summary.guest is not None:
                print('ip: {}'.format(vm.summary.guest.ipAddress))
                return vm.summary.guest.ipAddress
            else:
                print('ip not assigned')
        else:
            print('vm not findable: {}'.format(vm_name))
    return None

@app.task
def task_list():
    #rows, columns = os.popen('stty size', 'r').read().split()
    rows = 10
    columns = 120

    # Calculating Terminal width to adjust columns size
    columns = int(columns) - 12  # remove the formatting layout size

    # The calculations here, reflect my personal preferences, you might need
    # to adapt for yours :-)
    timeSize = math.trunc(float(columns) / 100 * 1.0)
    userSize = math.trunc(float(columns) / 100.0 * 11.0)
    entityNameSize = math.trunc(float(columns) / 100.0 * 20.0)
    descriptionSize = math.trunc(float(columns) / 100.0 * 30.0)
    stateSize = math.trunc(float(columns) / 100.0 * 1.0)

    # Formatting Columns
    formatColumns = "%" + str(timeSize) + \
                    "s | %" + str(userSize) + \
                    "s | %" + str(entityNameSize) + \
                    "s | %" + str(descriptionSize) + \
                    "s | %" + str(stateSize) + \
                    "s"

    lastTask = None

    if validate_config():
        print("valid config")
    else:
        print("invalid config")
        return

    si = connect()

    if si:
        print("connection made to vcenter")
        atexit.register(Disconnect, si)
        content = si.RetrieveContent()

        while True:
            for task in content.taskManager.recentTask:
                try:
                    taskNum = task._moId.split("-")[1]

                    if lastTask == None or taskNum > lastTask:
                        lastTask = taskNum

                        # print the task information
                        print(formatColumns % (
                            str(task.info.startTime).split(".")[0],
                            task.info.reason.userName,
                            task.info.entityName,
                            task.info.descriptionId,
                            task.info.state
                        ))
                except Exception:
                    do = "nothing"
                    time.sleep(1)
    return 0
