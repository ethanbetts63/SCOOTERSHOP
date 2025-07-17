from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_GET
from ..decorators import admin_required
from inventory.models import SalesProfile


@require_GET
@admin_required
def search_sales_profiles_ajax(request):
    search_term = request.GET.get("query", "").strip()
    profiles_data = []

    if search_term:
        search_query = (
            Q(name__icontains=search_term)
            | Q(email__icontains=search_term)
            | Q(phone_number__icontains=search_term)
            | Q(address_line_1__icontains=search_term)
            | Q(address_line_2__icontains=search_term)
            | Q(country__icontains=search_term)
        )

        queryset = SalesProfile.objects.filter(search_query).distinct().order_by("name")

        for profile in queryset[:20]:
            profiles_data.append(
                {
                    "id": profile.pk,
                    "name": profile.name,
                    "email": profile.email,
                    "phone_number": profile.phone_number,
                }
            )

    return JsonResponse({"profiles": profiles_data})
