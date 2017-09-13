from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout
from django import forms

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
    host_os = forms.CharField(
        label="What OS would like you like on your VM?",
        widget=forms.Select(choices=TITLE_CHOICES),
        required=True,
    )

    core_count = forms.IntegerField(
        label="How many CPU cores would you like?",
        required=True,
        widget=forms.Select(choices=CORES)
    )

    memory_size = forms.IntegerField(
        label="How much memory would you like?",
        required=True,
        widget=forms.Select(choices=MEMORIES)
    )

    def __init__(self, *args, **kwargs):
        super(ExampleForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.form_method = 'post'
        self.helper.form_action = 'submit_survey'
        self.helper.form_class = 'form-horizontal'
        self.helper.add_input(Submit('submit', 'Submit'))
