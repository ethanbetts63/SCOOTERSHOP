# inventory/ajax/ajax_search_sales_profiles.py

from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required # Import for staff check
from inventory.models import SalesProfile # Import the SalesProfile model

@require_GET
@login_required
def search_sales_profiles_ajax(request):
    """
    AJAX endpoint to search for SalesProfile instances based on a query term.
    Searches across name, email, phone number, and linked user details.
    Returns a JSON response with a list of matching profiles (ID, name, email, phone).
    """
    # Ensure only staff members can access this endpoint
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    search_term = request.GET.get('query', '').strip()
    profiles_data = []

    if search_term:
        # Build a Q object for complex lookups across multiple fields and related models
        # Use '__icontains' for case-insensitive partial matches
        search_query = (
            Q(name__icontains=search_term) |
            Q(email__icontains=search_term) |
            Q(phone_number__icontains=search_term) |
            Q(address_line_1__icontains=search_term) |
            Q(address_line_2__icontains=search_term) |
            Q(country__icontains=search_term)
        )

        # Filter SalesProfile objects using the constructed Q object
        # Use .distinct() to avoid duplicate results if a profile matches multiple Q conditions
        queryset = SalesProfile.objects.filter(search_query).distinct().order_by('name') # Order for consistent display

        # Limit results to prevent overwhelming the client, e.g., first 20
        for profile in queryset[:20]:
            profiles_data.append({
                'id': profile.pk,
                'name': profile.name,
                'email': profile.email,
                'phone_number': profile.phone_number,
                # Add any other basic info you want to display in search results for the admin
            })

    return JsonResponse({'profiles': profiles_data})

