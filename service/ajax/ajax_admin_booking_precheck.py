# service/ajax/admin_booking_precheck.py
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from service.forms import AdminBookingDetailsForm # Assuming AdminBookingDetailsForm is here
# You might also need to import ServiceBookingUserForm and CustomerMotorcycleForm
# from service.forms import ServiceBookingUserForm, CustomerMotorcycleForm

@require_POST
def admin_booking_precheck_ajax(request):
    """
    AJAX endpoint to perform validation and gather warnings for admin booking forms.
    Returns JSON indicating errors, warnings, or if valid.
    """
    admin_form = AdminBookingDetailsForm(request.POST)
    # user_form = ServiceBookingUserForm(request.POST, prefix='user') # Example with prefix
    # motorcycle_form = CustomerMotorcycleForm(request.POST, prefix='motorcycle')

    response_data = {
        'status': 'success', # default success
        'errors': {},
        'warnings': []
    }

    # Validate AdminBookingDetailsForm first
    if admin_form.is_valid():
        warnings = admin_form.get_warnings()
        if warnings:
            response_data['status'] = 'warnings'
            response_data['warnings'] = [str(w) for w in warnings] # Convert lazy strings
    else:
        response_data['status'] = 'errors'
        response_data['errors']['admin_booking_details'] = admin_form.errors.as_json()

    # You would repeat this for ServiceBookingUserForm and CustomerMotorcycleForm
    # For example:
    # if user_form.is_valid():
    #     # No warnings on user form by design, but check for any errors
    #     pass
    # else:
    #     response_data['status'] = 'errors'
    #     response_data['errors']['user_profile'] = user_form.errors.as_json()
    #
    # if motorcycle_form.is_valid():
    #     pass
    # else:
    #     response_data['status'] = 'errors'
    #     response_data['errors']['motorcycle'] = motorcycle_form.errors.as_json()

    return JsonResponse(response_data)