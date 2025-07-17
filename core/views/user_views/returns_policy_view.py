from django.views.generic import TemplateView
from django.shortcuts import redirect
from dashboard.models import SiteSettings


class ReturnsPolicyView(TemplateView):
    template_name = "core/information/returns.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        site_settings = SiteSettings.get_settings()
        context["settings"] = site_settings
        return context

    def dispatch(self, request, *args, **kwargs):
        site_settings = SiteSettings.get_settings()
        if not site_settings.enable_returns_page and not request.user.is_staff:
            return redirect("core:index")
        return super().dispatch(request, *args, **kwargs)
