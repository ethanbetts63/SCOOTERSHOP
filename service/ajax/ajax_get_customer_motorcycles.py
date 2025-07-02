                  

from django.http import JsonResponse
from service.models import ServiceProfile, CustomerMotorcycle                            
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET


@require_GET
def get_customer_motorcycles_ajax(request, profile_id):
    #--
    try:
                                          
        service_profile = get_object_or_404(ServiceProfile, pk=profile_id)
    except Exception as e:
                                                                                      
        return JsonResponse({'error': f'ServiceProfile not found or invalid ID: {e}'}, status=404)

                                                       
                                                     
    motorcycles = CustomerMotorcycle.objects.filter(service_profile=service_profile).order_by('brand', 'model')

                                    
    motorcycle_data = []
    for mc in motorcycles:
        motorcycle_data.append({
            'id': mc.pk,
            'brand': mc.brand,
            'model': mc.model,
            'year': mc.year,                                         
            'rego': mc.rego,
                                                                             
        })

    return JsonResponse({'motorcycles': motorcycle_data})
