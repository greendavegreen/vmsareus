# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-10-10 17:57
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vmleases', '0005_auto_20170928_1302'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vm',
            name='vm_state',
            field=models.CharField(choices=[(b'q', b'queued'), (b'c', b'creating'), (b'i', b'ipaddr'), (b'u', b'useraccount'), (b's', b'stash'), (b'd', b'driveclone'), (b'p', b'prep'), (b'b', b'building'), (b'r', b'ready'), (b'a', b'aborted')], default=b'q', max_length=1),
        ),
    ]