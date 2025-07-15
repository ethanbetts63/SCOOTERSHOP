from django.views.generic import TemplateView
from django.contrib import messages
from django.urls import reverse

from core.mixins import AdminRequiredMixin
from refunds.models import RefundRequest


class IntermediaryRefundProcessingView(AdminRequiredMixin, TemplateView):

    template_name = "refunds/intermediary_refund_processing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        refund_request_pk = self.kwargs.get("pk")

        if not refund_request_pk:
            messages.error(
                self.request, "No refund request ID provided for processing."
            )
            return context

        try:

            RefundRequest.objects.filter(pk=refund_request_pk).exists()
            context["refund_request_pk"] = refund_request_pk

            context["process_refund_url"] = reverse(
                "refunds:process_refund", kwargs={"pk": refund_request_pk}
            )
        except Exception:
            messages.error(self.request, "Refund request not found or invalid.")
            context["refund_request_pk"] = None

        return context
