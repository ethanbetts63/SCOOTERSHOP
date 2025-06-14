# inventory/ajax/get_available_appointment_times_for_date.py

import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from inventory.models import InventorySettings
from inventory.utils.get_available_appointment_times import get_available_appointment_times

@require_GET
def get_available_appointment_times_for_date(request):
    # Change 'date' to 'selected_date' to match the frontend request
    selected_date_str = request.GET.get('selected_date')

    if not selected_date_str:
        return JsonResponse({'error': 'Date parameter (selected_date) is missing.'}, status=400)

    try:
        selected_date = datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

    inventory_settings = InventorySettings.objects.first()
    if not inventory_settings:
        return JsonResponse({'error': 'Inventory settings not found.'}, status=500)

    available_times_raw = get_available_appointment_times(selected_date, inventory_settings)

    # Format times to include both value (HH:MM) and display (HH:MM AM/PM)
    formatted_times = []
    for time_str in available_times_raw:
        try:
            # Parse the HH:MM string back to a time object to format it for display
            time_obj = datetime.datetime.strptime(time_str, '%H:%M').time()
            formatted_times.append({
                "value": time_str,
                "display": time_obj.strftime('%I:%M %p') # e.g., "09:00 AM"
            })
        except ValueError:
            # Fallback if parsing fails, just use the raw string for display
            formatted_times.append({
                "value": time_str,
                "display": time_str
            })

    return JsonResponse({'available_times': formatted_times})

