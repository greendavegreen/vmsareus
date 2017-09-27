import os
from django.conf import settings

from setup_ssh import setup_ssh_for_user

if not settings.configured:
    # set the default Django settings module for the 'celery' program.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')  # pragma: no cover

setup_ssh_for_user('192.168.117.3', 'davidgr', '00ChangeThis', 10)
