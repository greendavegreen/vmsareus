from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Vm, HostOsOption, MemoryOption, CPUOption

admin.site.register(Vm)
admin.site.register(HostOsOption)
admin.site.register(MemoryOption)
admin.site.register(CPUOption)
