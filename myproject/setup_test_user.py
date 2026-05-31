#!/usr/bin/env python
"""Create or update a superuser from environment variables.

Defaults are intentionally provided to match the requested demo credentials,
but you should always override these with environment variables in production.

Environment variables:
  ADMIN_USERNAME (default: admin2026)
  ADMIN_PASSWORD (default: @dm1n!2814)
  ADMIN_EMAIL    (default: admin@riverdale.ac.zw)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

USERNAME = os.environ.get('ADMIN_USERNAME', 'admin2026')
PASSWORD = os.environ.get('ADMIN_PASSWORD', '@dm1n!2814')
EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@riverdale.ac.zw')

if not USERNAME or not PASSWORD:
    print('ERROR: ADMIN_USERNAME and ADMIN_PASSWORD must be set')
    raise SystemExit(1)

user, created = User.objects.get_or_create(username=USERNAME, defaults={'email': EMAIL})
user.email = EMAIL
user.is_staff = True
user.is_superuser = True
user.set_password(PASSWORD)
user.save()

if created:
    print(f"✓ Superuser '{USERNAME}' created")
else:
    print(f"✓ Superuser '{USERNAME}' updated (password reset)")

print('---')
print(f'Username: {USERNAME}')
print(f'Email: {EMAIL}')
print('\nImportant: keep these credentials secure. Prefer setting them using environment variables in production.')
