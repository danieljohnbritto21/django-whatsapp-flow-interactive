from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static

def home(request):
    return JsonResponse({
        "message": "Thaagam Foundation WhatsApp Donation System",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "webhook": "/webhook/",
            "debug": "/debug/",
            "test": "/test/",
            "admin": "/admin/"
        }
    })

urlpatterns = [
    # Home
    path("", home, name="home"),
    
    # Admin
    path("admin/", admin.site.urls),
    
    # WhatsApp App URLs - includes webhook, debug, test, etc.
    path("", include("whatsapp_app.urls")),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)