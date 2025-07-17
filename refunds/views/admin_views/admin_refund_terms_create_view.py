from django.shortcuts import render, redirect
from django.views import View
from django.urls import reverse
from django.contrib import messages

from dashboard.mixins import AdminRequiredMixin
from refunds.forms import AdminRefundTermsForm


from refunds.models import RefundSettings


class AdminRefundTermsCreateView(AdminRequiredMixin, View):
    template_name = "refunds/admin_refund_terms_create.html"
    form_class = AdminRefundTermsForm

    def get(self, request, *args, **kwargs):
        settings = RefundSettings.objects.first()
        initial_content = ""
        if settings:
            initial_content = settings.generate_policy_text()

        form = self.form_class(initial={"content": initial_content})
        context = {
            "form": form,
            "page_title": "Create New Refund Policy Version",
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            terms_version = form.save(commit=False)

            terms_version.is_active = True
            terms_version.save()

            messages.success(
                request,
                f"New Refund Policy Version {terms_version.version_number} created successfully and set as active.",
            )
            return redirect(reverse("refunds:refund_terms_management"))
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                "form": form,
                "page_title": "Create New Refund Policy Version",
            }
            return render(request, self.template_name, context)
