import json

import os
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from vmsareus.taskapp.bus_logic import td_exists
from vmsareus.vmleases.api_funcs import star_branch_exists
from .models import Vm

#
# from django.forms import CharField
# from django.core import validators
#
# class SlugField(CharField):
#     default_validators = [validators.validate_slug]
#
#     from django import forms
#
#     class ContactForm(forms.Form):
#         # Everything as before.
#         ...
#
#         def clean_recipients(self):
#             data = self.cleaned_data['recipients']
#             if "fred@example.com" not in data:
#                 raise forms.ValidationError("You have forgotten about Fred!")
#
#             # Always return a value to use as the new cleaned data, even if
#             # this method didn't change it.
#             return data
#
#
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

    def clean_branch_name(self):
        data = self.cleaned_data['branch_name']
        if not star_branch_exists(data):
            raise ValidationError("No branch with this name exists.")
        if not td_exists(data):
            raise ValidationError("Branch exists, but has no TravellingDrive.  Use another branch or force DevCI to create one.")
        return data

    def __init__(self, *args, **kwargs):
        super(ExampleForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.form_method = 'post'
        self.helper.form_action = 'submit_survey'
        self.helper.form_class = 'form-horizontal'
        self.helper.add_input(Submit('submit', 'Submit'))
