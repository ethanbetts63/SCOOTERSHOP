                                                                           

from django.db.models import Q
from django.views.generic import ListView
from inventory.models import SalesProfile
from inventory.mixins import AdminRequiredMixin

class SalesProfileManagementView(AdminRequiredMixin, ListView):
    model = SalesProfile
    template_name = 'inventory/admin_sales_profile_management.html'
    context_object_name = 'sales_profiles'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().order_by('name')
        search_term = self.request.GET.get('q', '').strip()

        if search_term:
            queryset = queryset.filter(
                Q(name__icontains=search_term) |
                Q(email__icontains=search_term) |
                Q(phone_number__icontains=search_term) |
                Q(address_line_1__icontains=search_term) |
                Q(city__icontains=search_term) |
                Q(state__icontains=search_term) |
                Q(post_code__icontains=search_term) |
                Q(country__icontains=search_term)
            ).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_term'] = self.request.GET.get('q', '')
        context['page_title'] = "Sales Profiles Management"
        return context
