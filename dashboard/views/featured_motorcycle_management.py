from django.views.generic import TemplateView
from inventory.models import FeaturedMotorcycle

class FeaturedMotorcycleManagementView(TemplateView):
    template_name = "dashboard/featured_motorcycle_management.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['featured_new'] = FeaturedMotorcycle.objects.filter(motorcycle__condition='new').order_by('order')
        context['featured_used'] = FeaturedMotorcycle.objects.filter(motorcycle__condition='used').order_by('order')
        return context
