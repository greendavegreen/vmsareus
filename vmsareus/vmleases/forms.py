from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout
from django import forms
import json

from .models import Vm

TITLE_CHOICES = (
    ('win10', 'Your Friendly Windows 10 VM'),
    ('cent7', 'latest centos'),
)
CORES = (
    (1, '1 core'),
    (12, '12 cores'),
)
MEMORIES = (
    (4, '4 Gigabytes'),
    (16, '32 Gigabytes'),
)

class VmForm2(forms.ModelForm):

    class Meta:
        model = Vm
        fields = ('core_count', 'memory_size', 'host_os')
        widgets = {
            'host_os': forms.Select(choices=TITLE_CHOICES),
        }


class ExampleForm(forms.Form):
    hosts =[]
    with open('host_os_choices.json') as host_data_file:
        host_data = json.load(host_data_file)
    for h in host_data:
        hosts.append([h["template_name"], h["display_name"]])

    mem =[]
    with open('memory_choices.json') as memory_data_file:
        memory_list = json.load(memory_data_file)
    for m in memory_list:
        mem.append([m,m])


    cpu =[]
    with open('cpu_choices.json') as cpu_data_file:
        cpu_list = json.load(cpu_data_file)
    for c in cpu_list:
         cpu.append([c, c])


    host_os = forms.CharField(
        label="What OS would like you like on your VM?",
        widget=forms.Select(choices=hosts),
        required=True,
    )

    core_count = forms.IntegerField(
        label="How many CPU cores would you like?",
        required=True,
        widget=forms.Select(choices=cpu)
    )

    memory_size = forms.IntegerField(
        label="How much memory would you like?",
        required=True,
        widget=forms.Select(choices=mem)
    )

    def __init__(self, *args, **kwargs):
        super(ExampleForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.form_method = 'post'
        self.helper.form_action = 'submit_survey'
        self.helper.form_class = 'form-horizontal'
        self.helper.add_input(Submit('submit', 'Submit'))
