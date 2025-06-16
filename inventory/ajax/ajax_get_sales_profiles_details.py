# inventory/ajax/ajax_get_sales_profile_details.py

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from inventory.models import SalesProfile # Import the SalesProfile model

@require_GET
@login_required
def get_sales_profile_details_ajax(request, pk):
    """
    AJAX endpoint to retrieve detailed information for a specific SalesProfile.
    Returns a JSON response with all fields necessary to populate the display area.
    """
    # Ensure only staff members can access this endpoint
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    try:
        sales_profile = get_object_or_404(SalesProfile, pk=pk)
    except Exception as e:
        # Return a 404 error if the profile is not found
        return JsonResponse({'error': f'Sales Profile not found or invalid ID: {e}'}, status=404)

    # Serialize all relevant fields from the SalesProfile instance
    # This should include all fields you might want to display in the admin form
    profile_details = {
        'id': sales_profile.pk,
        'name': sales_profile.name,
        'email': sales_profile.email,
        'phone_number': sales_profile.phone_number,
        'address_line_1': sales_profile.address_line_1,
        'address_line_2': sales_profile.address_line_2,
        'city': sales_profile.city,
        'state': sales_profile.state,
        'post_code': sales_profile.post_code,
        'country': sales_profile.country,
        'drivers_license_number': sales_profile.drivers_license_number,
        'drivers_license_expiry': str(sales_profile.drivers_license_expiry) if sales_profile.drivers_license_expiry else None, # Convert date to string
        'date_of_birth': str(sales_profile.date_of_birth) if sales_profile.date_of_birth else None, # Convert date to string
        # Include a URL for the driver's license image if it exists, for display purposes
        'drivers_license_image_url': sales_profile.drivers_license_image.url if sales_profile.drivers_license_image else None,
        # Potentially include linked user info if relevant for display
        'user_username': sales_profile.user.username if sales_profile.user else None,
        'user_email': sales_profile.user.email if sales_profile.user else None,
    }

    return JsonResponse({'profile_details': profile_details})

