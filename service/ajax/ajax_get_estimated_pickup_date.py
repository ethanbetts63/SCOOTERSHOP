                                                

from django.http import JsonResponse
from django.views.decorators.http import require_GET
                                                                        
from service.models import ServiceType 
import datetime

from service.utils.calculate_estimated_pickup_date import calculate_estimated_pickup_date

@require_GET
def get_estimated_pickup_date_ajax(request):
    #--
    service_type_id = request.GET.get('service_type_id')
    service_date_str = request.GET.get('service_date')

                                             
    if not service_type_id or not service_date_str:
        return JsonResponse({'error': 'Missing service_type_id or service_date'}, status=400)

    try:
                                                                     
        service_type = ServiceType.objects.get(pk=service_type_id) 
        service_date = datetime.datetime.strptime(service_date_str, '%Y-%m-%d').date()
    except ServiceType.DoesNotExist:
                                                                   
        return JsonResponse({'error': 'ServiceType not found'}, status=404)
    except ValueError:
                                               
        return JsonResponse({'error': 'Invalid date format. ExpectedYYYY-MM-DD.'}, status=400)
    except Exception as e:
                                                     
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)

                                                                                   
                                                                                
                                                                       
    class MockBookingInstance:
        def __init__(self, service_type, service_date):
            self.service_type = service_type
            self.service_date = service_date
            self.estimated_pickup_date = None                             
        
        def save(self, update_fields=None):
            pass                                       

    mock_booking = MockBookingInstance(service_type, service_date)

                                                                            
    calculated_date = calculate_estimated_pickup_date(mock_booking)

    if calculated_date:
        return JsonResponse({
            'estimated_pickup_date': calculated_date.strftime('%Y-%m-%d')
        })
    else:
                                                                   
        return JsonResponse({'error': 'Could not calculate estimated pickup date'}, status=500)

