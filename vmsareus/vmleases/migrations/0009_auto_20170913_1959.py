# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-09-13 19:59
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vmleases', '0008_auto_20170913_1954'),
    ]

    operations = [
        migrations.RenameField(
            model_name='memoryoption',
            old_name='core_count',
            new_name='gigabyte_count',
        ),
    ]