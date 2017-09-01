# Create your models here.
from django.db import models
from django.utils import timezone
from dateutil.relativedelta import relativedelta

def get_deadline():
    return timezone.now() + relativedelta(months=1)

class Vm(models.Model):
    CORES = (
        (1, '1 core'),
        (12, '12 cores'),
    )
    MEMORIES = (
        (4, '4 Gigabytes'),
        (16, '32 Gigabytes'),
    )
    OS_CHOICES = (
        ('ubumini', 'Ubuntu mini image'),
        ('win10dev', 'Windows 10 developer image'),
    )
    STATES = (
        ('q', 'queued'),
        ('c', 'creating'),
        ('r', 'running'),
        ('a', 'aborted'),
    )

    author = models.ForeignKey('users.User', on_delete=models.CASCADE)

    core_count = models.IntegerField(choices=CORES)
    memory_size = models.IntegerField(choices=MEMORIES)
    host_os = models.CharField(max_length=32, choices=OS_CHOICES, default='ubumini')

    vm_state = models.CharField(max_length=1, choices=STATES, default='q')
    vm_name = models.CharField(max_length=64, default='')

    created_date = models.DateTimeField(default=timezone.now)
    expires_date = models.DateTimeField(default=get_deadline)

    # def __str__(self):
    #     return super.
