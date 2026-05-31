#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth.models import User

# Delete existing test user if exists
User.objects.filter(username='admin123').delete()

# Create new test user
user = User.objects.create_user(
    username='admin123',
    email='admin@riverdale.ac.zw',
    password='admin',
    is_staff=True,
    is_superuser=True
)

print("✓ Test user created successfully!")
print("─" * 50)
print(f"Username: admin123")
print(f"Password: admin")
print(f"Email: admin@riverdale.ac.zw")
print(f"Is Staff: {user.is_staff}")
print(f"Is Superuser: {user.is_superuser}")
print("─" * 50)
print("\nYou can now login at: http://localhost:8000/login/")
