                                                                   

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

from service.models import ServiceType

@user_passes_test(lambda u: u.is_staff)
def toggle_service_type_active_status(request, pk):
    if request.method == 'POST':
        service_type = get_object_or_404(ServiceType, pk=pk)
        service_type.is_active = not service_type.is_active
        service_type.save()

        status_text = "activated" if service_type.is_active else "deactivated"
        messages.success(request, f"Service type '{service_type.name}' has been {status_text}.")

        return JsonResponse({'status': 'success', 'is_active': service_type.is_active, 'message': f"Service type '{service_type.name}' has been {status_text}."})
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)