from django.urls import path
from . import views

app_name = 'config'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('api/rfid-scan/', views.rfid_scan, name='rfid_scan'),
    path('api/last-scan/', views.last_scan, name='last_scan'),
    path('api/dashboard-data/', views.api_dashboard_data, name='dashboard_data'),
    path('api/cost/', views.api_cost, name='api_cost'),
    path('register/', views.student_register, name='student_register'),
    path('api/register/', views.student_register_ajax, name='student_register_ajax'),
    path('api/student-update/', views.student_update_ajax, name='student_update_ajax'),
    path('api/student-delete/', views.student_delete_ajax, name='student_delete_ajax'),
    path('topup/', views.topup, name='topup'),
    path('students/', views.students_page, name='students'),
    path('cost/', views.update_cost, name='update_cost'),
    path('api/toggle-active/', views.toggle_active, name='toggle_active'),
    path('api/health/', views.api_health, name='api_health'),
    path('api/bus/sync/', views.api_bus_sync, name='api_bus_sync'),
    path('api/bus/transaction/', views.api_bus_transaction, name='api_bus_transaction'),
    path('api/bus/wallets/', views.api_bus_wallets, name='api_bus_wallets'),
]
