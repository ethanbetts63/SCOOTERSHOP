from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('users.urls', namespace='users')),
    path('inventory/', include('inventory.urls', namespace='inventory')),
    path('service/', include('service.urls', namespace='service')),
    
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('', include('core.urls', namespace='core')),
    path('payments/', include('payments.urls', namespace="payments")),
    path('mailer/', include('mailer.urls', namespace='mailer'))
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
