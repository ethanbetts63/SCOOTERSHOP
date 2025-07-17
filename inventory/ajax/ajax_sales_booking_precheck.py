from django.http import JsonResponse
from django.views.decorators.http import require_POST
from ..decorators import admin_required
from inventory.forms import AdminSalesBookingForm


@require_POST
@admin_required
def sales_booking_precheck_ajax(request):
    form = AdminSalesBookingForm(request.POST)

    response_data = {"status": "success", "errors": {}, "warnings": []}

    if form.is_valid():
        warnings = form.get_warnings()
        if warnings:
            response_data["status"] = "warnings"
            response_data["warnings"] = [str(w) for w in warnings]
    else:
        response_data["status"] = "errors"
        errors_dict = {}
        for field, errors in form.errors.items():
            errors_dict[field] = [str(e) for e in errors]

        

        response_data["errors"] = errors_dict

    return JsonResponse(response_data)
