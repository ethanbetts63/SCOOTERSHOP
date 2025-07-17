from django.http import JsonResponse
from django.views.decorators.http import require_POST
from service.forms import AdminBookingDetailsForm
from ..decorators import admin_required


@require_POST
@admin_required
def admin_booking_precheck_ajax(request):
    admin_form = AdminBookingDetailsForm(request.POST)
    response_data = {"status": "success", "errors": {}, "warnings": []}

    if admin_form.is_valid():
        warnings = admin_form.get_warnings()
        if warnings:
            response_data["status"] = "warnings"
            response_data["warnings"] = [str(w) for w in warnings]
    else:
        response_data["status"] = "errors"
        response_data["errors"]["admin_booking_details"] = admin_form.errors.as_json()

    return JsonResponse(response_data)
