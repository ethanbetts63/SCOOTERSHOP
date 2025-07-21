from django.http import JsonResponse
from service.models import ServiceType
from service.utils.get_service_date_availibility import get_service_date_availability

def get_service_type_availability_ajax(request):
    service_type_id = request.GET.get("service_type_id")
    service_type = ServiceType.objects.get(id=service_type_id)
    min_date, disabled_dates_json = get_service_date_availability(service_type)
    return JsonResponse({"disabled_dates": disabled_dates_json})