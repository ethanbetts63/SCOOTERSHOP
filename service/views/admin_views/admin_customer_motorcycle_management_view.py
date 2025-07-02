                                                                        
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q                                      
from django.views.generic import ListView                                              
from service.models import CustomerMotorcycle                                                            

class CustomerMotorcycleManagementView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    
    model = CustomerMotorcycle
    template_name = 'service/admin_customer_motorcycle_management.html'               
    context_object_name = 'motorcycles'                                             
    paginate_by = 10                                                

    def test_func(self):
        
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_queryset(self):
        
        queryset = super().get_queryset().select_related('service_profile')                                           
        search_term = self.request.GET.get('q', '').strip()

        if search_term:
            queryset = queryset.filter(
                Q(brand__icontains=search_term) |
                Q(model__icontains=search_term) |
                Q(rego__icontains=search_term) |
                Q(vin_number__icontains=search_term) |
                Q(engine_number__icontains=search_term) |
                Q(service_profile__name__icontains=search_term) |                                        
                Q(service_profile__email__icontains=search_term)                                         
            ).distinct()                                                                            
        return queryset.order_by('-created_at')                                       

    def get_context_data(self, **kwargs):
        
        context = super().get_context_data(**kwargs)
        context['search_term'] = self.request.GET.get('q', '')                                               
        return context

