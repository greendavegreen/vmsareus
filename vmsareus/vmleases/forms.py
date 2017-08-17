from django import forms

from .models import Vm

class VmForm(forms.ModelForm):

    class Meta:
        model = Vm
        fields = ('core_count', 'memory_size', 'host_os')
