from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
import json
import datetime

from .models import RFIDTag, Student, Account, RideLog, SystemConfig
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
from django.views.decorators.http import require_http_methods
from django.core.cache import cache


def login_view(request):
	"""Handle user login with Django authentication"""
	if request.user.is_authenticated:
		return redirect('config:dashboard')
	
	if request.method == 'POST':
		username = request.POST.get('username', '').strip()
		password = request.POST.get('password', '')
		
		# Authenticate user against Django's auth system
		user = authenticate(request, username=username, password=password)
		
		if user is not None:
			login(request, user)
			messages.success(request, f'Welcome back, {user.username}!')
			return redirect('config:dashboard')
		else:
			messages.error(request, 'Invalid username or password.')
			return render(request, 'config/riverdale_login.html', {
				'username': username,
				'error': 'Invalid credentials'
			})
	
	return render(request, 'config/riverdale_login.html')


def logout_view(request):
	"""Handle user logout"""
	logout(request)
	messages.success(request, 'You have been logged out.')
	return redirect('config:login')


@login_required(login_url='config:login')
def dashboard(request):
	total_rides = RideLog.objects.filter(success=True).count()
	total_revenue = RideLog.objects.filter(success=True).aggregate(sum=Sum('fare'))['sum'] or 0
	recent_rides = RideLog.objects.select_related('student').order_by('-timestamp')[:10]
	students = Student.objects.count()

	chart_data = list(RideLog.objects.filter(success=True).order_by('-timestamp')[:20].values_list('fare', flat=True))

	# build students data for client-side UI
	students_qs = Student.objects.select_related('rfid_tag').all()
	students_list = []
	for s in students_qs:
		acct = Account.objects.filter(student=s).first()
		students_list.append({
			'id': s.id,
			'name': s.name,
			'rfidUid': s.rfid_tag.uid if s.rfid_tag else '',
			'balance': float(acct.balance) if acct else 0,
			'active': bool(s.rfid_tag and s.rfid_tag.assigned),
			# include related user info if present so frontend can show username/email
			'username': s.user.username if getattr(s, 'user', None) else None,
			'email': s.user.email if getattr(s, 'user', None) else None,
			# metadata fields persisted on Student
			'grade': s.grade,
			'roll': s.roll,
			'parent': s.parent_contact,
		})

	recent_qs = RideLog.objects.select_related('student').order_by('-timestamp')[:20]
	recent_list = []
	for r in recent_qs:
		recent_list.append({
			'studentName': r.student.name,
			'amount': float(-r.fare) if r.success else float(-r.fare),
			'description': 'RFID tap',
			# ISO-like timestamp (YYYY-MM-DD HH:MM:SS) for reliable client-side parsing
			'timestamp': timezone.localtime(r.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
			'type': 'payment' if r.success else 'failed'
		})

	return render(request, 'config/dashboard.html', {
		'total_rides': total_rides,
		'total_revenue': total_revenue,
		'recent_rides': recent_rides,
		'students': students,
		'chart_data': chart_data,
		'students_json': json.dumps(students_list),
		'transactions_json': json.dumps(recent_list),
		'cost_per_ride': float(SystemConfig.get_solo().cost_per_ride),
		'min_balance': float(SystemConfig.get_solo().min_balance),
	})


@csrf_exempt
def rfid_scan(request):
	if request.method != 'POST':
		return JsonResponse({'error': 'POST required'}, status=400)
	try:
		payload = json.loads(request.body.decode('utf-8'))
	except Exception:
		payload = request.POST

	uid = payload.get('uid') or payload.get('tag')
	# use configured cost per ride by default
	default_fare = SystemConfig.get_solo().cost_per_ride
	if 'fare' in payload and payload.get('fare') not in (None, '', []):
		try:
			fare = Decimal(str(payload.get('fare')))
		except Exception:
			fare = default_fare
	else:
		fare = default_fare

	if not uid:
		return JsonResponse({'error': 'missing uid'}, status=400)

	tag = RFIDTag.objects.filter(uid=uid).first()
	if not tag:
		# unknown tag - cache for dashboard polling so UI can show unregistered tag
		cache.set('last_scan', {
			'uid': uid,
			'student': None,
			'status': 'tag_not_found',
			'remaining': None,
			'timestamp': timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
		}, 30)
		return JsonResponse({'error': 'tag not found'}, status=404)
	if not tag.assigned:
		cache.set('last_scan', {
			'uid': uid,
			'student': None,
			'status': 'tag_unassigned',
			'remaining': None,
			'timestamp': timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
		}, 30)
		return JsonResponse({'error': 'tag unassigned'}, status=404)

	student = Student.objects.filter(rfid_tag=tag).first()
	if not student:
		cache.set('last_scan', {
			'uid': uid,
			'student': None,
			'status': 'student_not_found',
			'remaining': None,
			'timestamp': timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
		}, 30)
		return JsonResponse({'error': 'student not found for tag'}, status=404)

	account, _ = Account.objects.get_or_create(student=student)
	if account.balance < fare:
		RideLog.objects.create(student=student, fare=fare, success=False)
		cache.set('last_scan', {
			'uid': uid,
			'student': student.name,
			'status': 'insufficient_funds',
			'remaining': str(account.balance),
			'timestamp': timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
		}, 30)
		return JsonResponse({'status': 'insufficient_funds', 'balance': str(account.balance)}, status=402)

	account.balance -= fare
	account.save()
	RideLog.objects.create(student=student, fare=fare, success=True)

	# store last scan in cache for dashboard polling (short-lived)
	cache.set('last_scan', {
		'uid': uid,
		'student': student.name,
		'status': 'ok',
		'remaining': str(account.balance),
		'timestamp': timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
	}, 30)

	return JsonResponse({'status': 'ok', 'remaining': str(account.balance)})


@csrf_exempt
@require_http_methods(["POST"])
def update_cost(request):
	"""Update the cost per ride from the dashboard form. CSRF is exempted so the inline dashboard button works in demo mode."""
	cost = request.POST.get('cost')
	try:
		new_cost = Decimal(str(cost))
	except Exception:
		messages.error(request, 'Invalid cost value')
		return redirect('config:dashboard')

	cfg = SystemConfig.get_solo()
	cfg.cost_per_ride = new_cost
	cfg.save()
	messages.success(request, f'Cost per ride updated to ${new_cost}')
	return redirect('config:dashboard')


@require_http_methods(["GET", "POST"])
def api_cost(request):
	"""GET /api/cost/ - Get the current cost per ride from database.
	POST /api/cost/ - Update cost per ride via AJAX.
	
	GET Response: { 'cost': 25.00 }
	POST Body: { 'cost': 25.00 } (JSON or form-encoded)
	POST Response: { 'status': 'ok', 'cost': 25.00 }
	
	This allows real-time updates across all connected clients without page reload.
	"""
	if request.method == 'GET':
		cfg = SystemConfig.get_solo()
		cost = float(cfg.cost_per_ride)
		min_balance = float(cfg.min_balance)
		return JsonResponse({'cost': cost, 'min_balance': min_balance})

	# POST: Update cost
	try:
		if request.content_type == 'application/json':
			payload = json.loads(request.body.decode('utf-8'))
			cost = payload.get('cost')
		else:
			cost = request.POST.get('cost')
	except Exception:
		return JsonResponse({'status': 'error', 'message': 'Invalid payload'}, status=400)

	if cost is None or cost == '':
		return JsonResponse({'status': 'error', 'message': 'Cost is required'}, status=400)

	# validate and set cost
	try:
		new_cost = Decimal(str(cost))
		if new_cost < 0:
			return JsonResponse({'status': 'error', 'message': 'Cost cannot be negative'}, status=400)
	except Exception:
		return JsonResponse({'status': 'error', 'message': 'Invalid cost value'}, status=400)

	# optional: allow updating min_balance in same request
	min_balance = None
	try:
		if request.content_type == 'application/json':
			payload = json.loads(request.body.decode('utf-8'))
			min_balance = payload.get('min_balance') if 'min_balance' in payload else None
		else:
			min_balance = request.POST.get('min_balance')
	except Exception:
		min_balance = None

	cfg = SystemConfig.get_solo()
	cfg.cost_per_ride = new_cost
	# validate and set min_balance if provided
	if min_balance not in (None, '', []):
		try:
			new_min = Decimal(str(min_balance))
			cfg.min_balance = new_min
		except Exception:
			return JsonResponse({'status': 'error', 'message': 'Invalid min_balance value'}, status=400)

	cfg.save()

	return JsonResponse({'status': 'ok', 'cost': float(new_cost), 'min_balance': float(cfg.min_balance)}, status=200)


@require_http_methods(["GET", "POST"])
def student_register(request):
	if request.method == 'POST':
		name = request.POST.get('name')
		uid = request.POST.get('uid')
		username = request.POST.get('username')
		email = request.POST.get('email')
		balance = request.POST.get('balance')
		grade = request.POST.get('grade')
		roll = request.POST.get('roll')
		parent = request.POST.get('parent')
		if not name or not uid:
			messages.error(request, 'Name and UID required')
			return redirect('config:student_register')

		tag, created = RFIDTag.objects.get_or_create(uid=uid)
		tag.assigned = True
		tag.save()

		# create related User if provided
		user_obj = None
		if username or email:
			uname = username or (email.split('@')[0] if email and '@' in email else None)
			if uname:
				base = uname
				suffix = 0
				while User.objects.filter(username=uname).exists():
					suffix += 1
					uname = f"{base}{suffix}"
				user_obj = User.objects.create(username=uname, email=email or '')
				user_obj.set_unusable_password()
				user_obj.save()

		student = Student.objects.create(name=name, rfid_tag=tag, user=user_obj, grade=grade or None, roll=roll or None, parent_contact=parent or None)
		# initial balance if provided
		try:
			initial_balance = Decimal(str(balance)) if balance not in (None, '', []) else Decimal('0.00')
		except Exception:
			initial_balance = Decimal('0.00')
		Account.objects.create(student=student, balance=initial_balance)
		messages.success(request, f'Student {name} registered')
		return redirect('config:dashboard')

	return render(request, 'config/student_register.html')


@require_http_methods(["GET", "POST"])
def topup(request):
	if request.method == 'POST':
		uid = request.POST.get('uid')
		amount = request.POST.get('amount')
		try:
			amt = Decimal(amount)
		except Exception:
			messages.error(request, 'Invalid amount')
			return redirect('config:topup')

		tag = RFIDTag.objects.filter(uid=uid).first()
		if not tag:
			messages.error(request, 'Tag not found')
			return redirect('config:topup')
		student = Student.objects.filter(rfid_tag=tag).first()
		if not student:
			messages.error(request, 'Student not found for tag')
			return redirect('config:topup')

		account, _ = Account.objects.get_or_create(student=student)
		account.balance += amt
		account.save()
		messages.success(request, f'Added {amt} to {student.name}')
		return redirect('config:dashboard')

	return render(request, 'config/topup.html')


def students_page(request):
	students_qs = Student.objects.select_related('rfid_tag').all()
	students_list = []
	for s in students_qs:
		acct = Account.objects.filter(student=s).first()
		students_list.append({
			'id': s.id,
			'name': s.name,
			'rfidUid': s.rfid_tag.uid if s.rfid_tag else '',
			'balance': float(acct.balance) if acct else 0,
			'active': bool(s.rfid_tag and s.rfid_tag.assigned),
			'username': s.user.username if getattr(s, 'user', None) else None,
			'email': s.user.email if getattr(s, 'user', None) else None,
			'grade': s.grade,
			'roll': s.roll,
			'parent': s.parent_contact,
		})
	return render(request, 'config/students.html', { 'students_list': students_list })


@require_http_methods(["POST"])
def student_register_ajax(request):
	# Accept form-encoded or JSON
	try:
		if request.content_type == 'application/json':
			payload = json.loads(request.body.decode('utf-8'))
			name = payload.get('name')
			uid = payload.get('uid')
		else:
			name = request.POST.get('name')
			uid = request.POST.get('uid')
	except Exception:
		return JsonResponse({'status': 'error', 'message': 'Invalid payload'}, status=400)

	if not name or not uid:
		return JsonResponse({'status': 'error', 'message': 'Name and UID required'}, status=400)

	# optional fields
	username = payload.get('username') if isinstance(payload, dict) else request.POST.get('username')
	email = payload.get('email') if isinstance(payload, dict) else request.POST.get('email')
	balance = payload.get('balance') if isinstance(payload, dict) else request.POST.get('balance')
	grade = payload.get('grade') if isinstance(payload, dict) else request.POST.get('grade')
	roll = payload.get('roll') if isinstance(payload, dict) else request.POST.get('roll')
	parent = payload.get('parent') if isinstance(payload, dict) else request.POST.get('parent')
	active = payload.get('active') if isinstance(payload, dict) else request.POST.get('active')

	try:
		initial_balance = Decimal(str(balance)) if balance not in (None, '', []) else Decimal('0.00')
	except Exception:
		initial_balance = Decimal('0.00')

	tag, created = RFIDTag.objects.get_or_create(uid=uid)
	tag.assigned = bool(active) if active is not None else True
	tag.save()

	# prevent assigning the same RFID tag to multiple students (OneToOne constraint)
	existing_student = Student.objects.filter(rfid_tag=tag).first()
	if existing_student:
		return JsonResponse({'status': 'error', 'message': f'RFID tag {tag.uid} already assigned to {existing_student.name}.'}, status=400)

	user_obj = None
	if username or email:
		uname = username or (email.split('@')[0] if email and '@' in email else None)
		if uname:
			# ensure unique username
			base = uname
			suffix = 0
			while User.objects.filter(username=uname).exists():
				suffix += 1
				uname = f"{base}{suffix}"
			user_obj = User.objects.create(username=uname, email=email or '')
			user_obj.set_unusable_password()
			user_obj.save()

	student = Student.objects.create(name=name, rfid_tag=tag, user=user_obj)
	# save metadata fields on student record (grade, roll, parent_contact)
	if grade:
		student.grade = grade
	if roll:
		student.roll = roll
	if parent:
		student.parent_contact = parent
	student.save()
	acct = Account.objects.create(student=student, balance=initial_balance)

	# attach extra metadata to response (grade, roll, parent) even if not stored in model
	data = {
		'id': student.id,
		'name': student.name,
		'rfidUid': tag.uid,
		'balance': float(acct.balance),
		'active': bool(tag.assigned),
		'username': user_obj.username if user_obj else None,
		'email': user_obj.email if user_obj else None,
		'grade': student.grade,
		'roll': student.roll,
		'parent': student.parent_contact,
	}
	return JsonResponse({'status': 'ok', 'student': data}, status=201)


@require_http_methods(["POST"])
def student_update_ajax(request):
	"""Update an existing student's metadata (AJAX)."""
	try:
		payload = json.loads(request.body.decode('utf-8')) if request.content_type == 'application/json' else request.POST
	except Exception:
		return JsonResponse({'status': 'error', 'message': 'Invalid payload'}, status=400)

	sid = payload.get('id') or payload.get('student_id')
	if not sid:
		return JsonResponse({'status': 'error', 'message': 'Student id required'}, status=400)

	student = Student.objects.filter(id=sid).first()
	if not student:
		return JsonResponse({'status': 'error', 'message': 'Student not found'}, status=404)

	# fields to update
	name = payload.get('name') or payload.get('full_name')
	uid = payload.get('uid')
	username = payload.get('username')
	email = payload.get('email')
	balance = payload.get('balance')
	grade = payload.get('grade')
	roll = payload.get('roll')
	parent = payload.get('parent')

	if name:
		student.name = name

	# handle RFID tag assignment
	if uid:
		tag, _ = RFIDTag.objects.get_or_create(uid=uid)
		tag.assigned = True
		tag.save()
		student.rfid_tag = tag

	# handle user creation/update
	user_obj = student.user
	if username or email:
		if user_obj:
			if username:
				user_obj.username = username
			if email:
				user_obj.email = email
			user_obj.save()
		else:
			# create user ensuring unique username
			uname = username or (email.split('@')[0] if email and '@' in email else None)
			if uname:
				base = uname
				suffix = 0
				while User.objects.filter(username=uname).exists():
					suffix += 1
					uname = f"{base}{suffix}"
				user_obj = User.objects.create(username=uname, email=email or '')
				user_obj.set_unusable_password()
				user_obj.save()
				student.user = user_obj

	# update other metadata
	if grade is not None:
		student.grade = grade or None
	if roll is not None:
		student.roll = roll or None
	if parent is not None:
		student.parent_contact = parent or None

	student.save()

	# update balance if provided
	if balance is not None:
		try:
			acct = Account.objects.get(student=student)
		except Account.DoesNotExist:
			acct = Account.objects.create(student=student, balance=Decimal('0.00'))
		try:
			acct.balance = Decimal(str(balance))
			acct.save()
		except Exception:
			pass

	acct = Account.objects.filter(student=student).first()

	data = {
		'id': student.id,
		'name': student.name,
		'rfidUid': student.rfid_tag.uid if student.rfid_tag else '',
		'balance': float(acct.balance) if acct else 0,
		'active': bool(student.rfid_tag and student.rfid_tag.assigned),
		'username': student.user.username if getattr(student, 'user', None) else None,
		'email': student.user.email if getattr(student, 'user', None) else None,
		'grade': student.grade,
		'roll': student.roll,
		'parent': student.parent_contact,
	}
	return JsonResponse({'status': 'ok', 'student': data})


@require_http_methods(["POST"])
def student_delete_ajax(request):
	try:
		payload = json.loads(request.body.decode('utf-8')) if request.content_type == 'application/json' else request.POST
	except Exception:
		return JsonResponse({'status': 'error', 'message': 'Invalid payload'}, status=400)

	sid = payload.get('id') or payload.get('student_id')
	if not sid:
		return JsonResponse({'status': 'error', 'message': 'Student id required'}, status=400)

	student = Student.objects.filter(id=sid).first()
	if not student:
		return JsonResponse({'status': 'error', 'message': 'Student not found'}, status=404)

	# unassign tag if present
	if student.rfid_tag:
		try:
			tag = student.rfid_tag
			tag.assigned = False
			tag.save()
		except Exception:
			pass

	# delete related account and ride logs
	Account.objects.filter(student=student).delete()
	RideLog.objects.filter(student=student).delete()

	student.delete()
	return JsonResponse({'status': 'ok', 'message': 'Deleted'})


@require_http_methods(["POST"])
def toggle_active(request):
	"""Toggle the active state (RFID tag assigned) for a student's device.
	Expects JSON { "id": <student_id> } or form-encoded POST.
	Returns JSON { 'status': 'ok', 'active': true/false }.
	"""
	try:
		payload = json.loads(request.body.decode('utf-8')) if request.content_type == 'application/json' else request.POST
	except Exception:
		return JsonResponse({'status': 'error', 'message': 'Invalid payload'}, status=400)

	sid = payload.get('id') or payload.get('student_id')
	if not sid:
		return JsonResponse({'status': 'error', 'message': 'Student id required'}, status=400)

	student = Student.objects.filter(id=sid).first()
	if not student:
		return JsonResponse({'status': 'error', 'message': 'Student not found'}, status=404)

	if not student.rfid_tag:
		return JsonResponse({'status': 'error', 'message': 'Student has no RFID tag assigned'}, status=400)

	tag = student.rfid_tag
	tag.assigned = not bool(tag.assigned)
	tag.save()

	return JsonResponse({'status': 'ok', 'active': bool(tag.assigned)})


def last_scan(request):
	"""Return the last RFID scan stored in cache (for frontend polling)."""
	data = cache.get('last_scan') or {}
	return JsonResponse({'last_scan': data})


def api_dashboard_data(request):
	"""Return students and recent transactions as JSON for dashboard JS polling."""
	students_qs = Student.objects.select_related('rfid_tag').all()
	students_list = []
	for s in students_qs:
		acct = Account.objects.filter(student=s).first()
		students_list.append({
			'id': s.id,
			'name': s.name,
			'rfidUid': s.rfid_tag.uid if s.rfid_tag else '',
			'balance': float(acct.balance) if acct else 0,
			'active': bool(s.rfid_tag and s.rfid_tag.assigned),
			'username': s.user.username if getattr(s, 'user', None) else None,
			'email': s.user.email if getattr(s, 'user', None) else None,
			'grade': s.grade,
			'roll': s.roll,
			'parent': s.parent_contact,
		})

	recent_qs = RideLog.objects.select_related('student').order_by('-timestamp')[:50]
	recent_list = []
	for r in recent_qs:
		recent_list.append({
			'studentName': r.student.name,
			'amount': float(-r.fare) if r.success else float(-r.fare),
			'description': 'RFID tap',
			'timestamp': timezone.localtime(r.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
			'type': 'payment' if r.success else 'failed'
		})

	return JsonResponse({'students': students_list, 'transactions': recent_list})


# ----------------------------------------------------------------
# Bus firmware API endpoints  (WiFi variant -- riverdale-code-wifi)
# ----------------------------------------------------------------

def api_health(request):
	"""GET /api/health/  -- firmware liveness check."""
	return JsonResponse({'status': 'ok'})


def api_bus_sync(request):
	"""GET /api/bus/sync/?bus_id=<id>
	Returns the configured fare and all active students with their server-side balances.
	The bus_id query param is accepted for future per-bus filtering but currently ignored.
	"""
	fare = float(SystemConfig.get_solo().cost_per_ride)
	students_qs = (
		Student.objects
		.select_related('rfid_tag')
		.filter(rfid_tag__isnull=False, rfid_tag__assigned=True)
	)
	students_list = []
	for s in students_qs:
		acct = Account.objects.filter(student=s).first()
		students_list.append({
			'rfid': s.rfid_tag.uid,
			'balance': float(acct.balance) if acct else 0.0,
		})
	return JsonResponse({'fare': fare, 'students': students_list})


@csrf_exempt
def api_bus_transaction(request):
	"""POST /api/bus/transaction/
	Body: {"rfid":"AABBCCDD","fare":25.00,"timestamp":1716000000,"bus_id":"bus1"}
	Logs the ride and deducts the fare from the server-side balance.
	A subsequent wallet-push will override the balance, so this acts as a safe fallback.
	"""
	if request.method != 'POST':
		return JsonResponse({'error': 'POST required'}, status=400)
	try:
		data = json.loads(request.body.decode('utf-8'))
	except Exception:
		return JsonResponse({'error': 'invalid JSON'}, status=400)

	rfid = data.get('rfid')
	fare_raw = data.get('fare')
	ts_unix = data.get('timestamp')
	bus = data.get('bus_id', '')

	if not rfid or fare_raw is None:
		return JsonResponse({'error': 'rfid and fare required'}, status=400)
	try:
		fare = Decimal(str(fare_raw))
	except Exception:
		return JsonResponse({'error': 'invalid fare'}, status=400)

	if ts_unix:
		try:
			ts = datetime.datetime.fromtimestamp(int(ts_unix), tz=datetime.timezone.utc)
		except Exception:
			ts = timezone.now()
	else:
		ts = timezone.now()

	tag = RFIDTag.objects.filter(uid=rfid).first()
	if not tag:
		return JsonResponse({'error': 'tag not found'}, status=404)
	student = Student.objects.filter(rfid_tag=tag).first()
	if not student:
		return JsonResponse({'error': 'student not found'}, status=404)

	account, _ = Account.objects.get_or_create(student=student)
	success = account.balance >= fare
	if success:
		account.balance -= fare
		account.save()

	RideLog.objects.create(student=student, fare=fare, success=success, timestamp=ts, bus_id=bus)

	# Update last_scan cache so the dashboard reflects bus taps in real time
	cache.set('last_scan', {
		'uid': rfid,
		'student': student.name,
		'status': 'ok' if success else 'insufficient_funds',
		'remaining': str(account.balance),
		'timestamp': timezone.localtime(ts).strftime('%Y-%m-%d %H:%M:%S'),
		'bus_id': bus,
	}, 30)

	return JsonResponse({'status': 'ok', 'balance': str(account.balance)}, status=200)


@csrf_exempt
def api_bus_wallets(request):
	"""POST /api/bus/wallets/
	Body: {"bus_id":"bus1","students":[{"rfid":"AABBCCDD","balance":125.00},...] }
	Bulk-updates student balances. The ESP32 is authoritative for balances after each sync.
	"""
	if request.method != 'POST':
		return JsonResponse({'error': 'POST required'}, status=400)
	try:
		data = json.loads(request.body.decode('utf-8'))
	except Exception:
		return JsonResponse({'error': 'invalid JSON'}, status=400)

	students_payload = data.get('students', [])
	if not isinstance(students_payload, list):
		return JsonResponse({'error': 'students must be a list'}, status=400)

	updated = 0
	not_found = 0
	for entry in students_payload:
		rfid = entry.get('rfid')
		balance_raw = entry.get('balance')
		if not rfid or balance_raw is None:
			continue
		try:
			balance = Decimal(str(balance_raw))
		except Exception:
			continue
		tag = RFIDTag.objects.filter(uid=rfid).first()
		if not tag:
			not_found += 1
			continue
		student = Student.objects.filter(rfid_tag=tag).first()
		if not student:
			not_found += 1
			continue
		acct, _ = Account.objects.get_or_create(student=student)
		acct.balance = balance
		acct.save()
		updated += 1

	return JsonResponse({'status': 'ok', 'updated': updated, 'not_found': not_found}, status=200)
