# payments/views/HireRefunds/admin_hire_refund_management.py
from django.contrib.admin.views.decorators import staff_member_required
from django.views.generic import ListView
from django.utils.decorators import method_decorator
from payments.models import HireRefundRequest

@method_decorator(staff_member_required, name='dispatch')
class AdminHireRefundManagement(ListView):
    model = HireRefundRequest
    template_name = 'payments/admin_hire_refund_management.html'
    context_object_name = 'refund_requests'
    paginate_by = 20 

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.GET.get('status')

        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = HireRefundRequest.STATUS_CHOICES
        context['current_status'] = self.request.GET.get('status', 'all')
        return context