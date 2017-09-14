import json
import os

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect

from vmsareus.taskapp import celery
from vmsareus.vmleases.forms import ExampleForm
from .models import Vm


# Create your views here.


@login_required
def vm_list(request):

    if request.user.is_superuser:
        vms = Vm.objects.all
    else:
        vms = Vm.objects.filter(author=request.user)

    return render(request, 'leases/vm_list.html', {'vms': vms})


@login_required
def vm_detail(request, pk):
    vm = get_object_or_404(Vm, pk=pk)
    info = celery.get_vm_info(vm.vm_name)
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

            print(config)
            vm = Vm(host_os=config['display_name'],
                    core_count=form.cleaned_data['core_count'],
                    memory_size=form.cleaned_data['memory_size'])
            # vm = form.save(commit=False)
            vm.author = request.user
            vm.save()

            # calculate values for template, cores, and memory from the submitted form

            celery.fill_lease.delay(vm.pk, config['template_name'], vm.core_count, vm.memory_size)

            return redirect('leases:vm_detail', pk=vm.pk)
    else:
        form = ExampleForm()
    return render(request, 'leases/vm_edit.html', {'form': form})

@login_required
def vm_remove(request, pk):
    vm = get_object_or_404(Vm, pk=pk)
    celery.delete_vm.delay(vm.vm_name)
    vm.delete()
    return redirect('leases:vm_list')

@login_required
def vm_extend(request, pk):
    vm = get_object_or_404(Vm, pk=pk)
    vm.expires_date = vm.expires_date + relativedelta(months=1)
    vm.save()
    return redirect('leases:vm_detail', pk=vm.pk)
