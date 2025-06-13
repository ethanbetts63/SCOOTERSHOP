# inventory/ajax/get_available_appointment_times_for_date.py

import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from inventory.models import InventorySettings
from inventory.utils.get_available_appointment_times import get_available_appointment_times

@require_GET
def get_available_appointment_times_for_date(request):
    selected_date_str = request.GET.get('date')

    if not selected_date_str:
        return JsonResponse({'error': 'Date parameter is missing.'}, status=400)

    try:
        selected_date = datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

    inventory_settings = InventorySettings.objects.first()
    if not inventory_settings:
        return JsonResponse({'error': 'Inventory settings not found.'}, status=500)

    available_times = get_available_appointment_times(selected_date, inventory_settings)

    formatted_times = [{"value": time_str, "text": time_str} for time_str in available_times]

    return JsonResponse({'available_times': formatted_times})
