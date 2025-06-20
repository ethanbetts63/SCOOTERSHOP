
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from service.models import ServiceProfile


@require_GET
def get_service_profile_details_ajax(request, profile_id):
    """
    AJAX endpoint to retrieve detailed information for a specific ServiceProfile.
    Returns a JSON response with all fields necessary to populate the ServiceBookingUserForm.
    This function is used when an admin selects a customer from search results to pre-fill their form.
    """
    try:
        profile = get_object_or_404(ServiceProfile, pk=profile_id)
    except Exception as e:
        # Return a 404 response if the profile is not found
        return JsonResponse({'error': f'ServiceProfile not found or invalid ID: {e}'}, status=404)

    # Serialize all relevant fields from the ServiceProfile instance
    # Ensure these fields match those expected by your ServiceBookingUserForm
    profile_details = {
        'id': profile.pk,
        'name': profile.name,
        'email': profile.email,
        'phone_number': profile.phone_number,
        'address_line_1': profile.address_line_1,
        'address_line_2': profile.address_line_2,
        'city': profile.city,
        'state': profile.state,
        'post_code': profile.post_code,
        'country': profile.country,
        'user_id': profile.user.pk if profile.user else None,
        'username': profile.user.username if profile.user else None,
    }

    return JsonResponse({'profile_details': profile_details})

