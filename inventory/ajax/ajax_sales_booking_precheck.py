from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from inventory.forms import AdminSalesBookingForm
from django import forms


@require_POST
@login_required
def sales_booking_precheck_ajax(request):

    if not request.user.is_staff:
        return JsonResponse({"error": "Permission denied"}, status=403)

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

        if forms.NON_FIELD_ERRORS in form.errors:
            errors_dict[forms.NON_FIELD_ERRORS] = [
                str(e) for e in form.errors[forms.NON_FIELD_ERRORS]
            ]

        response_data["errors"] = errors_dict

    return JsonResponse(response_data)
