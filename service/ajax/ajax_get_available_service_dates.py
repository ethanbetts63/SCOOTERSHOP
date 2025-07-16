from django.http import JsonResponse
from django.views.decorators.http import require_GET
import json
from ..decorators import admin_required

from ..utils import get_service_date_availability


@require_GET
def get_service_date_availability_ajax(request):
    try:
        min_date, disabled_dates_json = get_service_date_availability()

        disabled_dates = json.loads(disabled_dates_json)

        response_data = {
            "min_date": min_date.strftime("%Y-%m-%d"),
            "disabled_dates": disabled_dates,
            "warnings": [],
        }

        return JsonResponse(response_data)

    except Exception:
        return JsonResponse(
            {"error": "Could not retrieve service date availability."}, status=500
        )
