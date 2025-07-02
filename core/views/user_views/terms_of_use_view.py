from django.views.generic import TemplateView
from django.views.decorators.http import require_http_methods
from django.shortcuts import redirect
from dashboard.models import SiteSettings
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator


@method_decorator(
    user_passes_test(lambda u: u.is_staff, login_url="core:index"), name="dispatch"
)
class TermsOfUseView(TemplateView):
    template_name = "core/information/terms.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        site_settings = SiteSettings.get_settings()
        context["settings"] = site_settings
        return context

    def dispatch(self, request, *args, **kwargs):
        site_settings = SiteSettings.get_settings()
        if not site_settings.enable_terms_page and not request.user.is_staff:
            return redirect("core:index")
        return super().dispatch(request, *args, **kwargs)
