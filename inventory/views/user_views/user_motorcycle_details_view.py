from django.views.generic import DetailView
from django.http import Http404
from inventory.models import Motorcycle, InventorySettings
from inventory.utils.get_motorcycle_details import get_motorcycle_details
from inventory.utils.get_sales_faqs import get_faqs_for_step


class UserMotorcycleDetailsView(DetailView):
    model = Motorcycle
    template_name = "inventory/user_motorcycle_details.html"
    context_object_name = "motorcycle"
    pk_url_kwarg = "pk"

    def get_object(self, queryset=None):
        pk = self.kwargs.get(self.pk_url_kwarg)
        motorcycle = get_motorcycle_details(pk)
        if not motorcycle:
            raise Http404("Motorcycle not found or does not exist.")
        return motorcycle

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        inventory_settings = InventorySettings.objects.first()
        context["inventory_settings"] = inventory_settings

        context["sales_faqs"] = get_faqs_for_step("general")
        context["faq_title"] = "Questions About Our Motorcycles"

        return context
