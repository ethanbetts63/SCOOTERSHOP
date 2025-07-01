                                                                 

from django.views.generic import ListView
from inventory.models import Motorcycle
from inventory.utils.get_unique_makes_for_filter import get_unique_makes_for_filter
from inventory.utils.get_sales_faqs import get_faqs_for_step
import datetime


class MotorcycleListView(ListView):
    model = Motorcycle
    template_name = 'inventory/motorcycle_list.html'
    context_object_name = 'motorcycles'
    paginate_by = 10
    allow_empty = True

    def get_queryset(self):
        return Motorcycle.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        condition_slug = self.kwargs.get('condition_slug')

        unique_makes = get_unique_makes_for_filter(condition_slug=condition_slug)

        context['unique_makes'] = sorted(list(unique_makes))
        context['current_condition_slug'] = condition_slug
        context['page_title'] = f"{condition_slug.replace('-', ' ').title()} Motorcycles" if condition_slug else "All Motorcycles"

        current_year = datetime.date.today().year
        context['years'] = list(range(2000, current_year + 1))
        context['years'].reverse()

                             
        context['sales_faqs'] = get_faqs_for_step('general')
        context['faq_title'] = "Frequently Asked Questions"

        return context
