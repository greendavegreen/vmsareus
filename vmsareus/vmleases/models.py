# Create your models here.
from django.db import models
from django.utils import timezone


class Vm(models.Model):
    CORES = (
        (1, '1 core'),
        (8, '8 cores'),
        (12, '12 cores'),
    )
    MEMORIES = (
        (8, '8 Gigabytes'),
        (12, '12 Gigabytes'),
    )
    DISKS = (
        (100, '100 Gigabytes'),
        (200, '200 Gigabytes'),
    )

    author = models.ForeignKey('users.User', on_delete=models.CASCADE)
    core_count = models.IntegerField(choices=CORES)
    memory_size = models.IntegerField(choices=MEMORIES)
    disk_size = models.IntegerField(choices=DISKS)

    created_date = models.DateTimeField(
            default=timezone.now)

    # def __str__(self):
    #     return super.
