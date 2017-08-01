from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect

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
    return render(request, 'leases/vm_detail.html', {'vm': vm})


@login_required
def vm_new(request):
    if request.method == "POST":
        form = VmForm(request.POST)
        if form.is_valid():
            vm = form.save(commit=False)
            vm.author = request.user
            vm.save()
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
