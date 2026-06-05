#!/usr/bin/env python
"""Test unregistered tags using Django test client"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
sys.path.insert(0, 'myproject')
django.setup()

from django.test import Client
from config.models import UnregisteredTag
import json

client = Client()
BASE_URL = ""

print("=" * 70)
print("Testing Unregistered Tags API - Direct Django Test")
print("=" * 70)

# Clear all existing unregistered tags first
print("\n0. Clearing any existing unregistered tags...")
UnregisteredTag.objects.all().delete()
print(f"   Deleted. Current count: {UnregisteredTag.objects.count()}")

# Test 1: Check current count
print("\n1. GET /api/unregistered-tags/count/")
response = client.get('/api/unregistered-tags/count/')
print(f"   Status: {response.status_code}")
print(f"   Response: {response.json()}")

# Test 2: Simulate RFID scan with unregistered tag
print("\n2. POST /api/rfid-scan/ (with unregistered tag: UNREGISTERED_TAG_123)")
response = client.post('/api/rfid-scan/', {'uid': 'UNREGISTERED_TAG_123', 'fare': 1.50}, content_type='application/json')
print(f"   Status: {response.status_code}")
print(f"   Response: {response.json()}")

# Test 3: Check count again (should be increased)
print("\n3. GET /api/unregistered-tags/count/ (after scan)")
response = client.get('/api/unregistered-tags/count/')
data = response.json()
print(f"   Status: {response.status_code}")
print(f"   Response: {data}")

# Test 4: Get all unregistered tags
print("\n4. GET /api/unregistered-tags/")
response = client.get('/api/unregistered-tags/')
data = response.json()
print(f"   Status: {response.status_code}")
print(f"   Tags count: {len(data.get('unregistered_tags', []))}")
if data.get('unregistered_tags'):
    for tag in data['unregistered_tags']:
        print(f"      - UID: {tag['uid']}, Timestamp: {tag['timestamp']}")

# Test 5: Simulate another RFID scan
print("\n5. POST /api/rfid-scan/ (with another unregistered tag: ANOTHER_UNREGISTERED_456)")
response = client.post('/api/rfid-scan/', {'uid': 'ANOTHER_UNREGISTERED_456', 'fare': 1.50}, content_type='application/json')
print(f"   Status: {response.status_code}")
print(f"   Response: {response.json()}")

# Test 6: Get all unregistered tags again
print("\n6. GET /api/unregistered-tags/ (after second scan)")
response = client.get('/api/unregistered-tags/')
data = response.json()
print(f"   Status: {response.status_code}")
print(f"   Tags count: {len(data.get('unregistered_tags', []))}")
if data.get('unregistered_tags'):
    for tag in data['unregistered_tags']:
        print(f"      - UID: {tag['uid']}, Timestamp: {tag['timestamp']}")

# Test 7: Check final count
print("\n7. GET /api/unregistered-tags/count/ (before delete)")
response = client.get('/api/unregistered-tags/count/')
data = response.json()
print(f"   Status: {response.status_code}")
print(f"   Response: {data}")

print("\n" + "=" * 70)
print("✅ Test Data Created - Tags are now in database!")
print("=" * 70)
