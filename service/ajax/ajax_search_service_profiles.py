from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_GET
from service.models import ServiceProfile


@require_GET
def search_customer_profiles_ajax(request):

    search_term = request.GET.get("query", "").strip()
    profiles_data = []

    if search_term:

        queryset = (
            ServiceProfile.objects.filter(
                Q(name__icontains=search_term)
                | Q(email__icontains=search_term)
                | Q(phone_number__icontains=search_term)
                | Q(address_line_1__icontains=search_term)
                | Q(address_line_2__icontains=search_term)
                | Q(city__icontains=search_term)
                | Q(state__icontains=search_term)
                | Q(post_code__icontains=search_term)
                | Q(country__icontains=search_term)
                | Q(user__username__icontains=search_term)
                | Q(user__email__icontains=search_term)
            )
            .distinct()
            .order_by("name")
        )

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
