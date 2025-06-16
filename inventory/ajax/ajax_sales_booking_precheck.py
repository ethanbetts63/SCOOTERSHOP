# inventory/ajax/ajax_sales_booking_precheck.py

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from inventory.forms import AdminSalesBookingForm # Import your updated sales booking form
from django import forms

@require_POST
@login_required
def sales_booking_precheck_ajax(request):
    """
    AJAX endpoint to perform validation and gather warnings for the admin sales booking form.
    Returns JSON indicating errors, warnings, or if valid.
    """
    # Ensure only staff members can access this endpoint
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    # When creating the form, pass the initial instance if it's an edit view
    # The selected_profile_id and selected_motorcycle_id are expected in request.POST
    # along with other form fields.
    # For a precheck, we typically don't pass an instance from the database,
    # as we're just validating the data that the user has currently entered into the form.
    form = AdminSalesBookingForm(request.POST) 

    response_data = {
        'status': 'success', # default success
        'errors': {},
        'warnings': []
    }

    if form.is_valid():
        warnings = form.get_warnings()
        if warnings:
            response_data['status'] = 'warnings'
            response_data['warnings'] = [str(w) for w in warnings] # Convert lazy strings
    else:
        response_data['status'] = 'errors'
        # Collect errors for each field that failed validation
        errors_dict = {}
        for field, errors in form.errors.items():
            errors_dict[field] = [str(e) for e in errors] # Convert lazy strings
        
        # If there are non-field errors (e.g., from clean method's add_error), include them
        if forms.NON_FIELD_ERRORS in form.errors:
            errors_dict[forms.NON_FIELD_ERRORS] = [str(e) for e in form.errors[forms.NON_FIELD_ERRORS]]

        response_data['errors'] = errors_dict

    return JsonResponse(response_data)

