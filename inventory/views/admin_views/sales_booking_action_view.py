# SCOOTER_SHOP/inventory/views/admin_views/sales_booking_action_view.py

from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from django.contrib import messages
from inventory.models import SalesBooking
from inventory.forms import SalesBookingActionForm
from inventory.utils import confirm_sales_booking, reject_sales_booking
from inventory.mixins import AdminRequiredMixin

class SalesBookingActionView(AdminRequiredMixin, FormView):
    """
    A view to handle the confirmation or rejection of a SalesBooking.
    It takes the booking ID and action type from the URL.
    """
    template_name = 'inventory/admin_sales_booking_action.html'
    form_class = SalesBookingActionForm
    success_url = reverse_lazy('inventory:sales_bookings_management')

    def get_initial(self):
        """
        Populates initial form data from URL parameters.
        """
        initial = super().get_initial()
        initial['sales_booking_id'] = self.kwargs['pk']
        initial['action'] = self.kwargs['action_type']
        return initial

    def get_context_data(self, **kwargs):
        """
        Adds context data to the template, including the booking object
        and page title based on the action type.
        """
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
            # Redirecting in get_context_data isn't ideal, handle in dispatch
            # or rely on template to show 'not found'
            context['page_title'] = "Sales Booking Not Found"
            context['booking'] = None

        context['action_type'] = action_type # Pass action_type to template for conditional display
        return context

    def dispatch(self, request, *args, **kwargs):
        """
        Ensures the sales booking exists before proceeding.
        """
        try:
            SalesBooking.objects.get(pk=self.kwargs['pk'])
        except SalesBooking.DoesNotExist:
            messages.error(request, "The specified sales booking does not exist.")
            return self.handle_no_permission() # Redirects to LOGIN_URL if not authenticated/admin

        action_type = self.kwargs.get('action_type')
        if action_type not in ['confirm', 'reject']:
            messages.error(request, "Invalid action type specified.")
            return self.handle_no_permission() # Or redirect to a generic error page

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """
        Processes the valid form submission.
        """
        sales_booking_id = form.cleaned_data['sales_booking_id']
        action = form.cleaned_data['action']
        message = form.cleaned_data.get('message')
        send_notification = form.cleaned_data.get('send_notification', False)

        if action == 'confirm':
            result = confirm_sales_booking(sales_booking_id, message, send_notification)
        elif action == 'reject':
            result = reject_sales_booking(sales_booking_id, message, send_notification)
        else:
            messages.error(self.request, "Invalid action type provided.")
            return self.form_invalid(form) # Re-render form with errors if action is somehow invalid

        if result['success']:
            messages.success(self.request, result['message'])
            return super().form_valid(form)
        else:
            messages.error(self.request, result['message'])
            return self.form_invalid(form) # Stay on the form page with error
