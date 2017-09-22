import json

import os
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.conf import settings

from .models import Vm



class ExampleForm(forms.Form):
    print(settings.ROOT_DIR)

    hosts =[]
    with open(os.path.join(str(settings.ROOT_DIR),'host_os_choices.json')) as host_data_file:
        host_data = json.load(host_data_file)
    for h in host_data:
        hosts.append([h["template_name"], h["display_name"]])

    branch_name = forms.CharField(
        label="What feature branch would you liked checked out?",
        widget=forms.TextInput(attrs={'placeholder': 'Enter a branch name',
                                      'id': 'foobar'}),
        required=True,
    )

    host_os = forms.CharField(
        label="What OS would like you like on your VM?",
        widget=forms.Select(choices=hosts),
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super(ExampleForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.form_method = 'post'
        self.helper.form_action = 'submit_survey'
        self.helper.form_class = 'form-horizontal'
        self.helper.add_input(Submit('submit', 'Submit'))
