from django.urls import path
from . import views

urlpatterns = [
    # Main webhook endpoints
    path('', views.webhook, name='webhook_root'),
    path('webhook/', views.webhook, name='webhook'),
    path('webhook', views.webhook, name='webhook_no_slash'),
    
    # Debug and test endpoints
    path('debug/', views.debug_webhook, name='debug_webhook'),
    path('test/', views.test_webhook, name='test_webhook'),
    path('test-food/', views.test_food_items, name='test_food_items'),
    path('test-students/', views.test_students, name='test_students'),
    path('test-patients/', views.test_patients, name='test_patients'),
    
    # Other endpoints
    path('easebuzz-callback/', views.easebuzz_callback, name='easebuzz_callback'),
    path('upload-logo/', views.upload_logo, name='upload_logo'),
    path('flow-endpoint/', views.flow_endpoint, name='flow_endpoint'),
]