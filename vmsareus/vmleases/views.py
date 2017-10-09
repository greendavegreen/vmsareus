import json

import os
from celery import chain
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect

from vmsareus.taskapp.celery import attach_drive
from vmsareus.taskapp.celery import clean_stash_key
from vmsareus.taskapp.celery import create_account
from vmsareus.taskapp.celery import create_drive
from vmsareus.taskapp.celery import delete_vm
from vmsareus.taskapp.celery import fill_lease
from vmsareus.taskapp.celery import get_vm_info
from vmsareus.taskapp.celery import send_notify_email
from vmsareus.taskapp.celery import setup_ssh
from vmsareus.taskapp.celery import wait_for_ip
from vmsareus.vmleases.forms import ExampleForm
from .models import Vm


# Create your views here.

@login_required
def vm_list(request):

    if request.user.is_superuser:
        vms = Vm.objects.all()
    else:
        vms = Vm.objects.filter(author=request.user)

    for vm in vms:
        if vm.branch_name.startswith("feature/",):
            vm.short_branch_name = vm.branch_name[8:]
        else:
            vm.short_branch_name = vm.branch_name

    return render(request, 'leases/vm_list.html', {'vms': vms})


@login_required
def vm_detail(request, pk):
    vm = get_object_or_404(Vm, pk=pk)

    info = get_vm_info(vm.vm_name)
    if info:
        guest_os = info['os']
        guest_power = info['power']
        ip = info['ip']
    else:
        guest_os = 'unknown'
        guest_power = 'unknown'
        ip = 'unknkown'

    return render(request, 'leases/vm_detail.html', {'vm': vm,
                                                     'ip': ip,
                                                     'guest_os': guest_os,
                                                     'guest_power': guest_power})

@login_required
def vm_manage(request, pk):
    vm = get_object_or_404(Vm, pk=pk)

    return render(request, 'leases/vm_manage.html', {'vm': vm})


def get_os_info(requested_template):
    with open(os.path.join(str(settings.ROOT_DIR),'host_os_choices.json')) as host_data_file:
        host_data = json.load(host_data_file)
    for h in host_data:
        if h['template_name'] == requested_template:
            return h

    return None

@login_required
def vm_new(request):
    if request.method == "POST":
        form = ExampleForm(request.POST)
        if form.is_valid():
            config = get_os_info(form.cleaned_data['host_os'])
            vm = Vm(author=request.user,
                    host_os=config['display_name'],
                    host_template=config['template_name'],
                    branch_name=form.cleaned_data['branch_name'])
            vm.save()

            # execute serially, with any exception causing abort of the entire chain
            vm_id = vm.pk
            chain(fill_lease.si(vm_id),
                  wait_for_ip.si(vm_id),
                  create_account.si(vm_id),
                  setup_ssh.si(vm_id),
                  create_drive.si(vm_id),
                  attach_drive.si(vm_id),
                  send_notify_email.si(vm_id)).apply_async()

            return redirect('leases:vm_list')
    else:
        form = ExampleForm()
    return render(request, 'leases/vm_edit.html', {'form': form})

@login_required
def vm_remove(request, pk):
    vm = get_object_or_404(Vm, pk=pk)
    delete_vm.delay(vm.vm_name)
    clean_stash_key.delay(vm.stash_key_id)
    vm.delete()
    return redirect('leases:vm_list')

@login_required
def vm_extend(request, pk):
    vm = get_object_or_404(Vm, pk=pk)
    vm.expires_date = vm.expires_date + relativedelta(months=1)
    vm.save()
    return redirect('leases:vm_manage', pk=vm.pk)



