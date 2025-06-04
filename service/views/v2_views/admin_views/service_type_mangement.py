
from django.shortcuts import render
from django.views import View
from service.models import ServiceType

class ServiceTypeManagementView(View):
    """
    Class-based view for displaying a list of all service types.
    This replaces the function-based settings_service_types view.
    """
    template_name = 'dashboard/service_type_management.html' # Original template name from the provided HTML


    def get(self, request, *args, **kwargs):
        """
        Handles GET requests: retrieves all ServiceType objects and renders them
        using the specified template.
        """
        service_types = ServiceType.objects.all().order_by('name')
        context = {
            'page_title': 'Service Types Management',
            'service_types': service_types,
            'active_tab': 'service_types' # This was 'service_types' in the original function
        }
        return render(request, self.template_name, context)

