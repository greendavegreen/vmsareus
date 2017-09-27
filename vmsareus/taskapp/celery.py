from __future__ import absolute_import

import time

import os
from celery import Celery
from django.apps import apps, AppConfig
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.urls import reverse

from .account_tools import add_user_to_windows_machine
from .vmware_tools import create_cluster_vm
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
        time.sleep(10)
        obj = Vm.objects.get(pk=id)

        full_url = ''.join(['http://', get_current_site(None).domain, reverse('leases:vm_detail', args=[obj.id])])
        print('sending mail to {} about {}'.format(obj.author.email, full_url))

        send_mail(
            'Requested VM {} is ready!'.format(obj.vm_name),
            'Your VM has been cloned! More info can be found at {}'.format(full_url),
            'vmsareus@vmsareus.lebanon.cd-adapco.com',
            [obj.author.email],
            fail_silently=False,
        )
    except ObjectDoesNotExist:
        print('VM does not exist: {0!s}'.format(id))


@app.task()
def create_account(id, addr, user):
    from ..vmleases.models import Vm
    try:
        time.sleep(10)
        vm = Vm.objects.get(pk=id)
        generated_pw = add_user_to_windows_machine(addr, user)

        #set vm password and save
        if generated_pw:
            vm.initial_password = generated_pw
            vm.save()
            send_notify_email.delay(id)
        else:
            vm.vm_state = 'a'
            vm.save()
    except ObjectDoesNotExist:
        print('VM does not exist: {0!s}'.format(id))


@app.task
def wait_for_ip(id):
    from ..vmleases.models import Vm
    try:
        time.sleep(5)
        vm = Vm.objects.get(pk=id)

        while True:
            info = get_vm_info(vm.vm_name)
            if info:
                if info['ip']:
                    ip = info['ip']
                    print('{} has ip {}'.format(vm.vm_name, info['ip']))
                    create_account.delay(id, ip, vm.author.username)
                    break
            else:
                print('vm not found in vcenter {}'.format(vm.vm_name))
                break
            time.sleep(5)
    except ObjectDoesNotExist:
        print('VM does not exist: {0!s}'.format(id))


@app.task
def fill_lease(id, template_name, core_count, mem_gigs):
    from ..vmleases.models import Vm
    try:
        time.sleep(5)
        obj = Vm.objects.get(pk=id)

        if validate_config():
            obj.vm_state = 'c'
            obj.save()

            name = 'dev-vm-{}-{}'.format(obj.author.username, int(time.time()))
            if create_cluster_vm(template_name, core_count, mem_gigs, name):
                obj.vm_state = 'r'
                obj.vm_name = name
                obj.save()
                print('VM created:{} status {}'.format(name, obj.vm_state))
                wait_for_ip.delay(id)
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
def delete_vm(vm_name):
    delete_if_exists(vm_name)

