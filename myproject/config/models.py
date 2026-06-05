from django.db import models
from decimal import Decimal
from django.contrib.auth.models import User
from django.utils import timezone


class RFIDTag(models.Model):
	uid = models.CharField(max_length=64, unique=True)
	assigned = models.BooleanField(default=False)

	def __str__(self):
		return self.uid


class Student(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
	name = models.CharField(max_length=200)
	rfid_tag = models.OneToOneField(RFIDTag, on_delete=models.SET_NULL, null=True, blank=True)
	grade = models.CharField(max_length=128, null=True, blank=True)
	roll = models.CharField(max_length=64, null=True, blank=True)
	parent_contact = models.CharField(max_length=128, null=True, blank=True)

	def __str__(self):
		return self.name


class Account(models.Model):
	student = models.OneToOneField(Student, on_delete=models.CASCADE)
	balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

	def __str__(self):
		return f"{self.student.name} - {self.balance}"


class RideLog(models.Model):
	student = models.ForeignKey(Student, on_delete=models.CASCADE)
	timestamp = models.DateTimeField(default=timezone.now)
	fare = models.DecimalField(max_digits=6, decimal_places=2)
	success = models.BooleanField(default=True)
	bus_id = models.CharField(max_length=64, blank=True, default='')

	def __str__(self):
		return f"{self.student.name} @ {self.timestamp} - {self.fare}"


class SystemConfig(models.Model):
	"""Singleton-like model to store site-wide settings (cost per ride, etc.)."""
	cost_per_ride = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('1.00'))
	min_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

	def __str__(self):
		return f"SystemConfig: ${self.cost_per_ride}"

	@classmethod
	def get_solo(cls):
		obj = cls.objects.first()
		if not obj:
			obj = cls.objects.create(cost_per_ride=Decimal('1.00'))
		return obj


class UnregisteredTag(models.Model):
	"""Store unregistered RFID tags with timestamps when they are scanned."""
	uid = models.CharField(max_length=64)
	timestamp = models.DateTimeField(default=timezone.now, db_index=True)
	
	class Meta:
		ordering = ['-timestamp']
		indexes = [
			models.Index(fields=['-timestamp']),
		]

	def __str__(self):
		return f"{self.uid} @ {self.timestamp}"
