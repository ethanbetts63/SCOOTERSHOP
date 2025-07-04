from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.http import JsonResponse
import json
from decimal import Decimal
import datetime
from django.utils import timezone


from service.ajax.ajax_get_service_booking_details import (
    get_service_booking_details_json,
)


from ..test_helpers.model_factories import (
    ServiceBookingFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
    ServiceTypeFactory,
    PaymentFactory,
    UserFactory,
)



class AjaxGetServiceBookingDetailsTest(TestCase):

    def setUp(self):

        self.factory = RequestFactory()

        self.staff_user = UserFactory(
            is_staff=True, username="staffuser", email="staff@example.com"
        )

        self.regular_user = UserFactory(
            is_staff=False, username="regularuser", email="regular@example.com"
        )

        self.service_booking = ServiceBookingFactory(
            service_profile=ServiceProfileFactory(user=self.staff_user),
            service_type=ServiceTypeFactory(),
            customer_motorcycle=CustomerMotorcycleFactory(),
            payment=PaymentFactory(
                amount=Decimal("150.00"),
                status="paid",
                refund_policy_snapshot={"some_policy_detail": "value"},
            ),
            dropoff_date=timezone.localdate() + datetime.timedelta(days=7),
            dropoff_time=datetime.time(10, 0),
            service_date=timezone.localdate() + datetime.timedelta(days=7),
            estimated_pickup_date=timezone.localdate() + datetime.timedelta(days=9),
            booking_status="confirmed",
            customer_notes="Test notes for booking details.",
        )

    def test_get_service_booking_details_success(self):

        url = reverse(
            "service:admin_api_get_service_booking_details",
            args=[self.service_booking.pk],
        )
        request = self.factory.get(url)
        request.user = self.staff_user

        response = get_service_booking_details_json(request, pk=self.service_booking.pk)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)

        self.assertEqual(content["id"], self.service_booking.id)
        self.assertEqual(
            content["service_booking_reference"],
            self.service_booking.service_booking_reference,
        )
        self.assertEqual(
            content["customer_name"],
            self.service_booking.service_profile.user.get_full_name()
            or self.service_booking.service_profile.name,
        )
        self.assertEqual(
            content["service_date"],
            self.service_booking.service_date.strftime("%Y-%m-%d"),
        )
        self.assertEqual(
            content["dropoff_date"],
            self.service_booking.dropoff_date.strftime("%Y-%m-%d"),
        )
        self.assertEqual(
            content["dropoff_time"], self.service_booking.dropoff_time.strftime("%H:%M")
        )
        self.assertEqual(
            content["estimated_pickup_date"],
            self.service_booking.estimated_pickup_date.strftime("%Y-%m-%d"),
        )
        self.assertEqual(
            content["booking_status"], self.service_booking.get_booking_status_display()
        )
        self.assertEqual(content["customer_notes"], self.service_booking.customer_notes)

        self.assertIn("motorcycle_details", content)
        self.assertEqual(
            content["motorcycle_details"]["year"],
            int(self.service_booking.customer_motorcycle.year),
        )
        self.assertEqual(
            content["motorcycle_details"]["brand"],
            self.service_booking.customer_motorcycle.brand,
        )
        self.assertEqual(
            content["motorcycle_details"]["model"],
            self.service_booking.customer_motorcycle.model,
        )

        self.assertIn("service_type_details", content)
        self.assertEqual(
            content["service_type_details"]["name"],
            self.service_booking.service_type.name,
        )
        self.assertEqual(
            content["service_type_details"]["description"],
            self.service_booking.service_type.description,
        )
        self.assertAlmostEqual(
            Decimal(str(content["service_type_details"]["base_price"])),
            self.service_booking.service_type.base_price,
        )

        self.assertEqual(
            content["payment_method"], self.service_booking.get_payment_method_display()
        )
        self.assertEqual(
            content["payment_date"],
            self.service_booking.payment.created_at.strftime("%Y-%m-%d %H:%M"),
        )
        self.assertAlmostEqual(
            Decimal(str(content["payment_amount"])), self.service_booking.payment.amount
        )
        self.assertEqual(
            content["payment_status"], self.service_booking.get_payment_status_display()
        )

        self.assertIn("entitled_refund_amount", content)
        self.assertIn("refund_calculation_details", content)
        self.assertIn("refund_policy_applied", content)
        self.assertIn("refund_days_before_dropoff", content)
        self.assertIn("refund_request_status_for_booking", content)

        self.assertIsInstance(content["refund_calculation_details"], str)

    def test_get_service_booking_details_not_found(self):

        invalid_pk = self.service_booking.pk + 100

        url = reverse(
            "service:admin_api_get_service_booking_details", args=[invalid_pk]
        )
        request = self.factory.get(url)
        request.user = self.staff_user

        response = get_service_booking_details_json(request, pk=invalid_pk)

        self.assertEqual(response.status_code, 404)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)
        self.assertIn("error", content)
        self.assertEqual(content["error"], "Service Booking not found")

    def test_only_get_requests_allowed(self):

        url = reverse(
            "service:admin_api_get_service_booking_details",
            args=[self.service_booking.pk],
        )

        request = self.factory.post(url)
        request.user = self.staff_user

        response = get_service_booking_details_json(request, pk=self.service_booking.pk)

        self.assertEqual(response.status_code, 405)
