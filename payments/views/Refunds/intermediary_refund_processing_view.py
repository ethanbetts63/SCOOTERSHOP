# SCOOTER_SHOP/payments/views/intermediary_refund_processing_view.py

from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from payments.models import RefundRequest
from django.contrib import messages
from django.urls import reverse # Used for building the post URL

class IntermediaryRefundProcessingView(LoginRequiredMixin, TemplateView):
    """
    An intermediary view that displays a page which immediately
    submits a POST request to the actual ProcessRefundView.
    This is used to convert a GET redirect into a POST submission.
    """
    template_name = 'payments/intermediary_refund_processing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        refund_request_pk = self.kwargs.get('pk')

        if not refund_request_pk:
            messages.error(self.request, "No refund request ID provided for processing.")
            return context # Will show a blank page with an error message

        try:
            # Verify the refund request exists. No need to fetch the full object
            # if we just need its PK for the redirect.
            RefundRequest.objects.filter(pk=refund_request_pk).exists()
            context['refund_request_pk'] = refund_request_pk
            # Pass the URL for the POST submission to the template
            context['process_refund_url'] = reverse('payments:process_refund', kwargs={'pk': refund_request_pk})
        except Exception:
            messages.error(self.request, "Refund request not found or invalid.")
            context['refund_request_pk'] = None # Indicate it's not valid
        
        return context

    def dispatch(self, request, *args, **kwargs):
        # Optional: Add more robust checks here, e.g., if the user has permission
        # to process this refund request, or if the refund request is in a valid state.
        # For simplicity, we're relying on ProcessRefundView to handle most validation.
        return super().dispatch(request, *args, **kwargs)

