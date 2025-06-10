# service/views.py

from django.http import JsonResponse
from django.db.models import Q # Import Q for complex lookups
from django.views.decorators.http import require_GET
from service.models import ServiceProfile # Ensure ServiceProfile is imported

# ... (other imports and views you might have, including the motorcycle AJAX views) ...

@require_GET
def search_customer_profiles_ajax(request):
    """
    AJAX endpoint to search for ServiceProfile instances based on a query term.
    Returns a JSON response with a list of matching profiles (ID, name, email, phone).
    """
    search_term = request.GET.get('query', '').strip()
    profiles_data = []

    if search_term:
        # Use the same robust search logic from your ServiceProfileManagementView
        queryset = ServiceProfile.objects.filter(
            Q(name__icontains=search_term) |
            Q(email__icontains=search_term) |
            Q(phone_number__icontains=search_term) |
            Q(address_line_1__icontains=search_term) |
            Q(address_line_2__icontains=search_term) |
            Q(city__icontains=search_term) |
            Q(state__icontains=search_term) |
            Q(post_code__icontains=search_term) |
            Q(country__icontains=search_term) |
            Q(user__username__icontains=search_term) |
            Q(user__email__icontains=search_term)
        ).distinct().order_by('name') # Order for consistent display

        # Limit results to prevent overwhelming the client, e.g., first 10-20
        # You might want to make this configurable
        for profile in queryset[:20]:
            profiles_data.append({
                'id': profile.pk,
                'name': profile.name,
                'email': profile.email,
                'phone_number': profile.phone_number,
                # Add any other basic info you want to display in search results
            })

    return JsonResponse({'profiles': profiles_data})
