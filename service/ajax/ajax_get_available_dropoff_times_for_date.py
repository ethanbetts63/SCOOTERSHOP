import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from service.utils.get_available_service_dropoff_times import get_available_dropoff_times

@require_GET
def get_available_dropoff_times_for_date(request):
    """
    AJAX endpoint to return available drop-off times for a selected date.
    It relies on the frontend (Flatpickr) to ensure the date itself is valid
    (e.g., not blocked, within advance notice, on open days, not at max capacity).
    This endpoint focuses solely on calculating time slots based on operational
    hours and existing booking spacing for the given date.
    """
    selected_date_str = request.GET.get('date')

    if not selected_date_str:
        return JsonResponse({'error': 'Date parameter is missing.'}, status=400)

    try:
        selected_date = datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        # This error indicates a malformed date string, which the frontend should prevent.
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

    # Call the utility function to get available times based on settings and existing bookings.
    # The utility function itself handles the logic of start/end times and spacing.
    available_times = get_available_dropoff_times(selected_date)

    # Format times for the frontend (e.g., "09:00", "09:30")
    # The 'value' and 'text' fields are standard for populating select dropdowns in JS.
    formatted_times = [{"value": time_str, "text": time_str} for time_str in available_times]

    # Return the available times as a JSON response.
    return JsonResponse({'available_times': formatted_times})

