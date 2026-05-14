from django.contrib import admin
from .models import RFIDTag, Student, Account, RideLog, SystemConfig


@admin.register(RFIDTag)
class RFIDTagAdmin(admin.ModelAdmin):
	list_display = ('uid', 'assigned')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
	list_display = ('name', 'user', 'rfid_tag')


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
	list_display = ('student', 'balance')


@admin.register(RideLog)
class RideLogAdmin(admin.ModelAdmin):
	list_display = ('student', 'timestamp', 'fare', 'success')


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
	list_display = ('cost_per_ride',)
