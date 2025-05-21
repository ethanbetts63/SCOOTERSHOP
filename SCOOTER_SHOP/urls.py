# SCOOTER_SHOP/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django Admin site URLs
    path('admin/', admin.site.urls),
    path('accounts/', include('users.urls', namespace='users')),
    path('inventory/', include('inventory.urls', namespace='inventory')),
    path('service/', include('service.urls', namespace='service')),
    path('hire/', include('hire.urls', namespace='hire')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('', include('core.urls', namespace='core')),
    path('payments/', include('payments.urls', namespace="payments"))
]

# Serve static and media files in development mode (DEBUG=True)
# In production, a dedicated web server (like Nginx or Apache) should serve these files.
if settings.DEBUG:
    # Serve user-uploaded media files
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Serve static files (CSS, JS, images collected by collectstatic)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
