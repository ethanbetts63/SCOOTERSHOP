                                                             

from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib import messages

from service.models import BlockedServiceDate

class BlockedServiceDateDeleteView(View):
    #--
                                                                  
                          
                                           

    def post(self, request, pk, *args, **kwargs):
        #--
        blocked_date = get_object_or_404(BlockedServiceDate, pk=pk)
        try:
            blocked_date.delete()
            messages.success(request, 'Blocked service date deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting blocked service date: {e}')
                                                             
        return redirect('service:blocked_service_dates_management')

