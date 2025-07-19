from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.db import transaction
from inventory.models import Motorcycle, TempSalesBooking, InventorySettings
from decimal import Decimal
from django.contrib import messages


class InitiateBookingProcessView(View):
    def post(self, request, pk):
        motorcycle = get_object_or_404(Motorcycle, pk=pk)

        if not motorcycle.is_available:
            messages.warning(
                request,
                f"The {motorcycle.title} is currently reserved or sold and cannot be booked at this time.",
            )
            return redirect(
                reverse("inventory:motorcycle-detail", kwargs={"pk": motorcycle.pk})
            )

        deposit_required_for_flow_str = request.POST.get(
            "deposit_required_for_flow", "false"
        )
        deposit_required_for_flow = deposit_required_for_flow_str.lower() == "true"

        inventory_settings = InventorySettings.objects.first()
        if not inventory_settings:
            messages.error(
                request,
                "Inventory settings are not configured. Please contact support.",
            )
            return redirect(reverse("inventory:all"))

        with transaction.atomic():
            temp_booking = TempSalesBooking(
                motorcycle=motorcycle,
                deposit_required_for_flow=deposit_required_for_flow,
                booking_status="pending_details",
            )
            temp_booking.amount_paid = Decimal("0.00")
            temp_booking.save()

        request.session["temp_sales_booking_uuid"] = str(temp_booking.session_uuid)
        if "current_sales_booking_reference" in request.session:
            del request.session["current_sales_booking_reference"]

        return redirect(reverse("inventory:step1_sales_profile"))
