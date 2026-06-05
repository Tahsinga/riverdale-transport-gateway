# Authentication & Login System Setup Guide

## Overview

Your RFID Payment System now has a **complete authentication system** using Django's built-in auth framework. Users must log in before accessing the dashboard.

## How It Works

### **Login Flow**
```
User visits / or /dashboard/
    ↓
Not authenticated? 
    ↓
Redirect to /login/
    ↓
User enters username + password
    ↓
Django authenticates against User database
    ↓
If valid → Log in user → Redirect to dashboard
If invalid → Show error message → Stay on login page
```

## Quick Start

### **Step 1: Create Admin User**

Run this command in your terminal:

```bash
cd c:\Users\TASHINGA\Downloads\RFIDProject\riverdale-transport-gateway\myproject
python manage.py createsuperuser
```

Follow the prompts:
```
Username: admin
Email: admin@riverdale.ac.zw
Password: (enter a secure password)
```

### **Step 2: Start Django Server**

```bash
python manage.py runserver
```

### **Step 3: Access the Application**

1. Open browser: `http://localhost:8000/`
2. You'll be redirected to `/login/`
3. Enter credentials:
   - **Username**: `admin`
   - **Password**: (the one you created)
4. Click **Sign In** → You'll be logged in and redirected to the dashboard

### **Step 4: Logout**

Click the **Logout** button in the sidebar footer to log out and return to the login page.

## Features

### ✅ **Beautiful Login Page**
- Professional dark-themed login interface
- Smooth animations and transitions
- Real-time form validation
- Error messages displayed clearly

### ✅ **Session Management**
- Django session cookies handle authentication
- Users stay logged in across page reloads
- Logout clears session and redirects to login

### ✅ **Protected Dashboard**
- Dashboard requires authentication (uses `@login_required` decorator)
- If unauthenticated user tries to access dashboard, they're redirected to login
- Login URL: `/login/`

### ✅ **User Info Display**
- Sidebar shows logged-in user's name
- User avatar with first letter of username
- Clean logout button in sidebar

## File Changes

### 1. **Views** (`config/views.py`)
**Added Functions:**
- `login_view(request)` - Handles login form submission
- `logout_view(request)` - Logs out user and redirects to login

**Updated:**
- `dashboard(request)` - Now requires `@login_required` decorator

### 2. **URLs** (`config/urls.py`)
**Added Routes:**
```python
path('login/', views.login_view, name='login'),
path('logout/', views.logout_view, name='logout'),
```

### 3. **Templates**
- `riverdale_login.html` - Updated with real Django form
- `dashboard.html` - Added user info + logout button in sidebar

## Creating Additional Users

### **Via Admin Panel**
1. Go to `http://localhost:8000/admin/`
2. Login with superuser credentials
3. Click **Users** → **Add User**
4. Fill in username and password
5. Save

### **Via Django Shell**
```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User

# Create a new user
user = User.objects.create_user(
    username='operator',
    email='operator@riverdale.ac.zw',
    password='operatorpass123'
)
print(f"User {user.username} created successfully!")
```

### **Via Management Command**
Create a new file: `config/management/commands/create_users.py`

```python
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Create demo users for the system'

    def handle(self, *args, **options):
        users = [
            {'username': 'admin', 'password': 'admin123', 'email': 'admin@riverdale.ac.zw'},
            {'username': 'operator', 'password': 'op123', 'email': 'op@riverdale.ac.zw'},
        ]
        
        for user_data in users:
            if not User.objects.filter(username=user_data['username']).exists():
                User.objects.create_user(**user_data)
                self.stdout.write(f"✓ Created user: {user_data['username']}")
            else:
                self.stdout.write(f"✗ User already exists: {user_data['username']}")
```

Then run:
```bash
python manage.py create_users
```

## Protecting Other Views

To protect other views (like topup, students page, etc.), add the decorator:

```python
from django.contrib.auth.decorators import login_required

@login_required(login_url='config:login')
def topup(request):
    # This view is now protected
    ...
```

## Customizing Login Behavior

### **Redirect After Login**
By default, Django redirects to the `next` parameter or the dashboard. To customize:

Edit `config/views.py`:

```python
def login_view(request):
    if request.user.is_authenticated:
        return redirect('config:dashboard')
    
    if request.method == 'POST':
        # ... authentication code ...
        if user is not None:
            login(request, user)
            # Customize redirect target
            next_page = request.GET.get('next') or 'config:dashboard'
            return redirect(next_page)
```

### **Session Timeout**
Edit `myproject/settings.py`:

```python
# Session expires after 30 minutes of inactivity
SESSION_COOKIE_AGE = 1800  # in seconds

# Auto-logout on browser close
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
```

### **Remember Me Functionality**
The checkbox exists but isn't implemented. To add it:

```python
# In login_view
if request.POST.get('remember'):
    # 30 days
    request.session.set_expiry(30 * 24 * 60 * 60)
else:
    # Browser session only
    request.session.set_expiry(0)
```

## Troubleshooting

### **"Invalid username or password" message**
- **Cause**: Credentials don't match database
- **Fix**: 
  1. Go to admin panel and reset password
  2. Or create a new user via `createsuperuser`

### **Login page appears after every page reload**
- **Cause**: Session cookie not being set
- **Fix**: 
  1. Clear browser cookies for localhost
  2. Check `INSTALLED_APPS` includes `'django.contrib.sessions'`
  3. Check `SESSION_ENGINE` is configured in settings

### **Can't access admin panel after login**
- **Cause**: User is not marked as staff
- **Fix**: 
  1. In Django shell:
  ```python
  user = User.objects.get(username='admin')
  user.is_staff = True
  user.is_superuser = True
  user.save()
  ```

### **Logout button not working**
- **Cause**: URL might not exist
- **Fix**: Verify `path('logout/', views.logout_view, name='logout')` exists in urls.py

## Security Considerations

### ✅ **CSRF Protection**
- All POST forms include `{% csrf_token %}`
- Django middleware protects against CSRF attacks

### ✅ **Password Security**
- Passwords are hashed using Django's default PBKDF2 algorithm
- Never stored in plain text

### ✅ **Session Security**
- Session cookies are secure in production (HTTPS)
- Set `SESSION_COOKIE_SECURE = True` in production

### ✅ **HTTPS in Production**
Add to `settings.py` for production:
```python
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

## Testing Login System

### **Test 1: Valid Credentials**
1. Navigate to `/login/`
2. Enter: username=`admin`, password=`(your password)`
3. Click Sign In
4. **Expected**: Logged in, redirected to dashboard

### **Test 2: Invalid Username**
1. Navigate to `/login/`
2. Enter: username=`wronguser`, password=`anything`
3. Click Sign In
4. **Expected**: Error message, stay on login page

### **Test 3: Invalid Password**
1. Navigate to `/login/`
2. Enter: username=`admin`, password=`wrongpass`
3. Click Sign In
4. **Expected**: Error message, stay on login page

### **Test 4: Session Persistence**
1. Login to dashboard
2. Close browser (or clear session)
3. Refresh page
4. **Expected**: Redirected to login page (session expired)

### **Test 5: Logout**
1. Login to dashboard
2. Click Logout button in sidebar
3. **Expected**: Logged out, message shown, redirected to login

## Database Schema

### **User Model** (Django Built-in)
```
User
├── id (primary key)
├── username (unique)
├── password (hashed)
├── email
├── first_name
├── last_name
├── is_active (boolean)
├── is_staff (boolean)
├── is_superuser (boolean)
├── date_joined (timestamp)
└── last_login (timestamp)
```

## Next Steps

### **Advanced Features**
1. **Two-Factor Authentication** (2FA)
2. **OAuth Integration** (Google, Microsoft)
3. **LDAP/Active Directory** integration
4. **Email verification** on signup
5. **Password reset** via email

### **User Management**
1. Add role-based access control (RBAC)
2. Different dashboards for different user types
3. User activity logging
4. Admin user management interface

## Support

For questions:
1. Check Django documentation: https://docs.djangoproject.com/en/6.0/
2. Review code comments in `config/views.py`
3. Check browser console (F12) for JavaScript errors
4. Check Django logs for server errors

## Quick Reference

| URL | Purpose | Requires Login |
|-----|---------|---|
| `/login/` | Login page | No |
| `/logout/` | Logout & redirect | Yes |
| `/` | Dashboard | Yes (redirects to login if not) |
| `/admin/` | Django admin panel | Yes (superuser only) |
| `/api/cost/` | Cost API | No (public) |
| `/api/rfid-scan/` | RFID processing | No (for ESP32) |

---

**Your authentication system is now live!** 🎉
