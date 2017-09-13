# Create your models here.
from django.db import models
from django.utils import timezone
from dateutil.relativedelta import relativedelta


def get_deadline():
    return timezone.now() + relativedelta(months=1)


class MemoryOption(models.Model):
    gigabyte_count = models.IntegerField(default=8)

    def __str__(self):  # __unicode__ on Python 2
        return str(self.gigabyte_count)

class CPUOption(models.Model):
    core_count = models.IntegerField(default=1)

    def __str__(self):  # __unicode__ on Python 2
        return str(self.core_count)

class HostOsOption(models.Model):
    INIT_CHOICES = (
        (1, 'none'),
        (2, 'windows 10 ssh'),
    )
    template_name = models.CharField(max_length=128, default='')
    display_name = models.CharField(max_length=256, default='', unique=True)
    display_icon = models.IntegerField(choices=INIT_CHOICES)
    init_type = models.IntegerField(choices=INIT_CHOICES)
    alive = models.BooleanField(default=True)
    cpu_choices = models.ManyToManyField(CPUOption)
    mem_choices = models.ManyToManyField(MemoryOption)

    def __str__(self):  # __unicode__ on Python 2
        return self.display_name + ' -> ' + self.template_name


class Vm(models.Model):
    STATES = (
        ('q', 'queued'),
        ('c', 'creating'),
        ('r', 'running'),
        ('a', 'aborted'),
    )

    author = models.ForeignKey('users.User', on_delete=models.CASCADE)

    core_count = models.IntegerField()
    memory_size = models.IntegerField()
    host_os = models.CharField(max_length=32, default='ubumini')

    vm_state = models.CharField(max_length=1, choices=STATES, default='q')
    vm_name = models.CharField(max_length=64, default='')

    created_date = models.DateTimeField(default=timezone.now)
    expires_date = models.DateTimeField(default=get_deadline)

    # def __str__(self):
    #     return super.
