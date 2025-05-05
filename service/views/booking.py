from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
import datetime
from django.db.models import Q
from service.models import ServiceBooking, CustomerMotorcycle, ServiceType
from dashboard.models import SiteSettings
from service.forms import (
    ServiceDetailsForm,
    CustomerMotorcycleForm,
    ServiceBookingUserForm,
    ExistingCustomerMotorcycleForm,
)
from django.contrib.auth.decorators import login_required
from django.utils import timezone

SERVICE_BOOKING_SESSION_KEY = 'service_booking_data'

# Starts the service booking process.
def booking_start(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_service_booking:
        messages.error(request, "Service booking is currently disabled.")
        return redirect(reverse('core:index'))

    if SERVICE_BOOKING_SESSION_KEY in request.session:
        del request.session[SERVICE_BOOKING_SESSION_KEY]
    request.session.modified = True

    return redirect(reverse('service:service_step1'))

# Renders the service confirmed page.
def service_confirmed_view(request):
    return render(request, 'service/service_not_yet_confirmed.html')
