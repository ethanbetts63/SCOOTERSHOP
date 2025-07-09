from django.views.generic import TemplateView
from dashboard.models import SiteSettings

class TermsOfUseView(TemplateView):
    template_name = "core/information/terms.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        site_settings = SiteSettings.get_settings()
        context["settings"] = site_settings
        return context

    def dispatch(self, request, *args, **kwargs):
        site_settings = SiteSettings.get_settings()
        return super().dispatch(request, *args, **kwargs)
