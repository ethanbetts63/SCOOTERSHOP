# SCOOTER_SHOP/inventory/views/admin_views/sales_booking_action_view.py

from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from django.contrib import messages
from inventory.models import SalesBooking
from inventory.forms import SalesBookingActionForm
from inventory.utils.confirm_sales_booking import confirm_sales_booking
from inventory.utils.reject_sales_booking import reject_sales_booking
from django.contrib.auth.mixins import LoginRequiredMixin # Ensure LoginRequiredMixin is imported
from users.views.auth import is_admin # Assuming this utility exists for admin check

class SalesBookingActionView(LoginRequiredMixin, FormView): # Ensure LoginRequiredMixin is used
    template_name = 'inventory/admin_sales_booking_action.html'
    form_class = SalesBookingActionForm
    success_url = reverse_lazy('inventory:sales_bookings_management')

    def get_initial(self):
        initial = super().get_initial()
        sales_booking_id = self.kwargs['pk']
        action_type = self.kwargs['action_type']
        
        initial['sales_booking_id'] = sales_booking_id
        initial['action'] = action_type

        # Pre-fill refund amount if action is reject and booking exists with a deposit
        if action_type == 'reject':
            try:
                booking = SalesBooking.objects.get(pk=sales_booking_id)
                if booking.payment_status == 'deposit_paid' and booking.amount_paid:
                    initial['refund_amount'] = booking.amount_paid
            except SalesBooking.DoesNotExist:
                pass # Handled by dispatch/template, no need to raise here

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sales_booking_id = self.kwargs['pk']
        action_type = self.kwargs['action_type']

        try:
            booking = SalesBooking.objects.get(pk=sales_booking_id)
            context['booking'] = booking
            if action_type == 'confirm':
                context['page_title'] = f"Confirm Sales Booking: {booking.sales_booking_reference}"
                context['action_display'] = 'Confirm'
            elif action_type == 'reject':
                context['page_title'] = f"Reject Sales Booking: {booking.sales_booking_reference}"
                context['action_display'] = 'Reject'
            else:
                context['page_title'] = "Invalid Sales Booking Action"
                context['action_display'] = 'Invalid'
        except SalesBooking.DoesNotExist:
            messages.error(self.request, "Sales Booking not found.")
            context['page_title'] = "Sales Booking Not Found"
            context['booking'] = None

        context['action_type'] = action_type
        return context

    def dispatch(self, request, *args, **kwargs):
        try:
            SalesBooking.objects.get(pk=self.kwargs['pk'])
        except SalesBooking.DoesNotExist:
            messages.error(request, "The specified sales booking does not exist.")
            return self.handle_no_permission()

        action_type = self.kwargs.get('action_type')
        if action_type not in ['confirm', 'reject']:
            messages.error(request, "Invalid action type specified.")
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        sales_booking_id = form.cleaned_data['sales_booking_id']
        action = form.cleaned_data['action']
        
        # Pass the entire cleaned_data dictionary (or relevant parts) as form_data
        # The utility function will then extract 'message', 'send_notification', 'initiate_refund', 'refund_amount' from it.
        form_data_for_utility = {
            'message': form.cleaned_data.get('message'),
            'send_notification': form.cleaned_data.get('send_notification', False),
            'initiate_refund': form.cleaned_data.get('initiate_refund', False),
            'refund_amount': form.cleaned_data.get('refund_amount'),
        }

        if action == 'confirm':
            result = confirm_sales_booking(
                sales_booking_id=sales_booking_id,
                requesting_user=self.request.user, # Pass the logged-in user
                form_data=form_data_for_utility, # Pass the relevant form data
                send_notification=form_data_for_utility['send_notification'] # Still explicitly pass if needed
            )
        elif action == 'reject':
            result = reject_sales_booking(
                sales_booking_id=sales_booking_id,
                requesting_user=self.request.user, # Pass the logged-in user
                form_data=form_data_for_utility, # Pass the relevant form data
                send_notification=form_data_for_utility['send_notification'] # Still explicitly pass if needed
            )
        else:
            messages.error(self.request, "Invalid action type provided.")
            return self.form_invalid(form)

        if result['success']:
            messages.success(self.request, result['message'])
            return super().form_valid(form)
        else:
            messages.error(self.request, result['message'])
            return self.form_invalid(form)
