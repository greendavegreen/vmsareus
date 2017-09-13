from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Vm, HostOS, MemoryOption, CPUOption

admin.site.register(Vm)
admin.site.register(HostOS)
admin.site.register(MemoryOption)
admin.site.register(CPUOption)
