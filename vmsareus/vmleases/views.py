from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect

from vmsareus.taskapp import celery
from vmsareus.vmleases.forms import VmForm
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
    ip = celery.get_ip(vm.vm_name)
    info = celery.get_vm_info(vm.vm_name)
    if info:
        guest_os = info['os']
        guest_power = info['power']
    else:
        guest_os = 'unknown'
        guest_power = 'unknown'
    return render(request, 'leases/vm_detail.html', {'vm': vm,
                                                     'ip': ip,
                                                     'guest_os': guest_os,
                                                     'guest_power': guest_power})


@login_required
def vm_new(request):
    if request.method == "POST":
        form = VmForm(request.POST)
        if form.is_valid():
            vm = form.save(commit=False)
            vm.author = request.user
            vm.save()

            # calculate values for template, cores, and memory from the submitted form

            celery.fill_lease.delay(vm.pk, 'vmrus-win10', 12, 16)
            return redirect('leases:vm_detail', pk=vm.pk)
    else:
        form = VmForm()
    return render(request, 'leases/vm_edit.html', {'form': form})

@login_required
def vm_edit(request, pk):
    vm = get_object_or_404(Vm, pk=pk)
    if request.method == "POST":
        form = VmForm(request.POST, instance=vm)
        if form.is_valid():
            vm = form.save(commit=False)
            vm.author = request.user
            vm.save()
            return redirect('leases:vm_detail', pk=vm.pk)
    else:
        form = VmForm(instance=vm)
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
