from inventory.mixins import AdminRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Q
from inventory.models import FeaturedMotorcycle


class FeaturedMotorcycleManagementView(AdminRequiredMixin, TemplateView):
    template_name = "inventory/admin_featured_motorcycle_management.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        new_filter = Q(motorcycle__condition="new") | Q(
            motorcycle__conditions__name__iexact="new"
        )
        used_filter = Q(motorcycle__condition="used") | Q(
            motorcycle__conditions__name__iexact="used"
        )

        context["featured_new"] = (
            FeaturedMotorcycle.objects.filter(new_filter).distinct().order_by("order")
        )
        context["featured_used"] = (
            FeaturedMotorcycle.objects.filter(used_filter).distinct().order_by("order")
        )

        return context
