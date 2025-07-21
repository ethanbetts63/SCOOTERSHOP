from django.http import JsonResponse
from django.contrib import messages
from service.models import ServiceType
from service.decorators import admin_required
from service.utils.toggle_active_status import toggle_active_status

@admin_required
def toggle_service_type_active_status(request, pk):
    if request.method == "POST":
        service_type = toggle_active_status(ServiceType, pk)
        status_text = "activated" if service_type.is_active else "deactivated"
        messages.success(
            request, f"Service type '{service_type.name}' has been {status_text}."
        )
        return JsonResponse(
            {
                "status": "success",
                "is_active": service_type.is_active,
                "message": f"Service type '{service_type.name}' has been {status_text}.",
            }
        )
    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)
