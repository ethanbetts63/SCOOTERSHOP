
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from service.models import ServiceProfile


@require_GET
def get_service_profile_details_ajax(request, profile_id):
    
    try:
        profile = get_object_or_404(ServiceProfile, pk=profile_id)
    except Exception as e:
                                                           
        return JsonResponse({'error': f'ServiceProfile not found or invalid ID: {e}'}, status=404)

                                                                    
                                                                             
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

