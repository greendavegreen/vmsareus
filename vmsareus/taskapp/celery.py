from __future__ import absolute_import

import time

import os
from celery import Celery
from django.apps import apps, AppConfig
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.urls import reverse

from .account_tools import add_user_to_windows_machine, delete_stash_key, customize_git_params, setup_desktop_for_user
from .account_tools import setup_ssh_for_user
from .bus_logic import attach_dev_drive
from .bus_logic import make_dev_drive_for_branch
from .vmware_tools import clone_vm
from .vmware_tools import delete_if_exists
from .vmware_tools import get_vm_info
from .vmware_tools import validate_config

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
    print('Request: {0!r}'.format(self.request))  # pragma: no cover


@app.task
def send_notify_email(id):
    from ..vmleases.models import Vm
    try:
        vm = Vm.objects.get(pk=id)
        full_url = ''.join(['http://', get_current_site(None).domain, reverse('leases:vm_detail', args=[vm.id])])
        send_mail(
            'Requested VM {} is ready!'.format(vm.vm_name),
            'Your VM has been cloned! More info can be found at {}'.format(full_url),
            'vmsareus@vmsareus.lebanon.cd-adapco.com',
            [vm.author.email],
            fail_silently=False,
        )
    except:
        print('error sending mail to {} about {}'.format(vm.author.email, full_url))
        vm.vm_state = 'a'
        vm.save()
        raise
    else:
        print('sent mail to {} about {}'.format(vm.author.email, full_url))
        vm.vm_state = 'r'
        vm.save()


@app.task()
def setup_ssh(id):
    from ..vmleases.models import Vm
    try:
        vm = Vm.objects.get(pk=id)
        info = get_vm_info(vm.vm_name)
        addr = info['ip']
        key_id = setup_ssh_for_user(addr,
                                    vm.author.username,
                                    vm.starting_password,
                                    id)
    except:
        vm.vm_state = 'a'
        vm.save()
        raise
    else:
        vm.vm_state = 'd'
        vm.stash_key_id = key_id
        vm.save()

@app.task()
def setup_windows(id):
    from ..vmleases.models import Vm
    try:
        vm = Vm.objects.get(pk=id)
        info = get_vm_info(vm.vm_name)
        addr = info['ip']
        setup_desktop_for_user(addr,
                               vm.author.username,
                               vm.starting_password)
    except:
        vm.vm_state = 'a'
        vm.save()
        raise
    else:
        pass

@app.task()
def setup_git(id):
    from ..vmleases.models import Vm
    try:
        vm = Vm.objects.get(pk=id)
        info = get_vm_info(vm.vm_name)
        addr = info['ip']
        key_id = customize_git_params(addr,
                                    vm.author.username,
                                    vm.starting_password)
    except:
        vm.vm_state = 'a'
        vm.save()
        raise
    else:
        pass


@app.task()
def create_account(id):
    from ..vmleases.models import Vm
    try:
        vm = Vm.objects.get(pk=id)
        info = get_vm_info(vm.vm_name)
        addr = info['ip']
        new_user = vm.author.username
        generated_pw = add_user_to_windows_machine(addr, new_user)
    except:
        vm.vm_state = 'a'
        vm.save()
        raise
    else:
        vm.vm_state = 's'
        vm.starting_password = generated_pw
        vm.save()
        #send_notify_email.delay(id)


@app.task
def wait_for_ip(id):
    from ..vmleases.models import Vm
    try:
        vm = Vm.objects.get(pk=id)
        while True:
            info = get_vm_info(vm.vm_name)
            if info['ip']:
                break
            time.sleep(5)
    except:
        vm.vm_state = 'a'
        vm.save()
        raise
    else:
        vm.vm_state = 'u'
        vm.save()
        ip = info['ip']
        print('{} has ip {}'.format(vm.vm_name, info['ip']))
        #create_account.delay(id)

@app.task
def fill_lease(i_id):
    from ..vmleases.models import Vm
    time.sleep(5)
    try:
        vm = Vm.objects.get(pk=i_id)
        validate_config()
        vm.vm_state = 'c'
        vm.save()
        name = 'dev-vm-{}-{}'.format(vm.author.username, int(time.time()))
        clone_vm(vm.host_template, name)
        #create_cluster_vm(vm.host_template, name)
    except:
        vm.vm_state = 'a'
        vm.save()
        raise
    else:
        vm.vm_state = 'i'
        vm.vm_name = name
        vm.save()
        #wait_for_ip.delay(id)

@app.task
def delete_vm(vm_name):
    delete_if_exists(vm_name)

@app.task
def clean_stash_key(key_id):
    delete_stash_key(key_id)


@app.task()
def create_drive(id):
    from ..vmleases.models import Vm
    try:
        vm = Vm.objects.get(pk=id)
        validate_config()
        make_dev_drive_for_branch(vm.branch_name, id)
    except:
        vm.vm_state = 'a'
        vm.save()
        raise
    else:
        vm.vm_state = 'p'
        vm.save()


@app.task()
def attach_drive(id):
    from ..vmleases.models import Vm
    try:
        vm = Vm.objects.get(pk=id)
        validate_config()
        attach_dev_drive(vm.vm_name, vm.branch_name, id)
    except:
        vm.vm_state = 'a'
        vm.save()
        raise
    else:
        vm.vm_state = 'b'
        vm.save()
