# Create your models here.
from django.db import models
from django.utils import timezone
from dateutil.relativedelta import relativedelta


def get_deadline():
    return timezone.now() + relativedelta(months=1)

class Vm(models.Model):
    STATES = (
        ('q', 'queued'),
        ('c', 'creating'),
        ('i', 'ipaddr'),
        ('u', 'useraccount'),
        ('s', 'stash'),
        ('d', 'driveclone'),
        ('p', 'prep'),
        ('b', 'building'),
        ('r', 'ready'),
        ('a', 'aborted'),
    )

    author = models.ForeignKey('users.User', on_delete=models.CASCADE)

    branch_name = models.CharField(max_length=128, default='')
    host_os = models.CharField(max_length=64, default='Windows 10 latest/patched')
    host_template = models.CharField(max_length=128, default='win10pe-vmsareus')

    starting_password = models.CharField(max_length=128, default='')
    stash_key_id = models.IntegerField(default=0)

    vm_state = models.CharField(max_length=1, choices=STATES, default='q')
    vm_name = models.CharField(max_length=64, default='')

    created_date = models.DateTimeField(default=timezone.now)
    expires_date = models.DateTimeField(default=get_deadline)

    # def __str__(self):
    #     return super.
