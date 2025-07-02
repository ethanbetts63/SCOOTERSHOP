from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.http import JsonResponse
import json
from datetime import date, time, timedelta


from ..test_helpers.model_factories import (
    UserFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
    ServiceTypeFactory,
    ServiceBookingFactory,
    PaymentFactory,
)


from service.ajax.ajax_search_service_bookings import search_service_bookings_ajax


class AjaxSearchServiceBookingsTest(TestCase):

    def setUp(self):

        self.factory = RequestFactory()

        self.staff_user = UserFactory(
            username="admin_user", email="admin@example.com", is_staff=True
        )
        self.non_staff_user = UserFactory(
            username="regular_user", email="user@example.com", is_staff=False
        )

        self.profile1 = ServiceProfileFactory(
            name="John Doe", email="john.doe@example.com", phone_number="0411111111"
        )
        self.motorcycle1 = CustomerMotorcycleFactory(
            service_profile=self.profile1,
            brand="Honda",
            model="CBR600RR",
            year="2020",
            rego="JD001",
        )
        self.service_type1 = ServiceTypeFactory(
            name="Oil Change", description="Standard oil and filter replacement"
        )
        self.payment1 = PaymentFactory(status="paid")
        self.booking1 = ServiceBookingFactory(
            service_booking_reference="SVC-ABCDEF01",
            service_profile=self.profile1,
            customer_motorcycle=self.motorcycle1,
            service_type=self.service_type1,
            dropoff_date=date.today() + timedelta(days=5),
            dropoff_time=time(10, 0),
            booking_status="confirmed",
            payment_status="paid",
            payment=self.payment1,
            customer_notes="Customer prefers synthetic oil.",
        )

        self.profile2 = ServiceProfileFactory(
            name="Jane Smith", email="jane.smith@example.com", phone_number="0422222222"
        )
        self.motorcycle2 = CustomerMotorcycleFactory(
            service_profile=self.profile2,
            brand="Yamaha",
            model="YZF-R1",
            year="2022",
            rego="JS002",
        )
        self.service_type2 = ServiceTypeFactory(
            name="Tyre Replacement", description="Front and rear tyre replacement"
        )
        self.payment2 = PaymentFactory(status="deposit_paid")
        self.booking2 = ServiceBookingFactory(
            service_booking_reference="SVC-XYZ78902",
            service_profile=self.profile2,
            customer_motorcycle=self.motorcycle2,
            service_type=self.service_type2,
            dropoff_date=date.today() + timedelta(days=10),
            dropoff_time=time(14, 30),
            booking_status="pending",
            payment_status="deposit_paid",
            payment=self.payment2,
            customer_notes="Need urgent service for racing.",
        )

        self.profile3 = ServiceProfileFactory(
            name="Bob Johnson", email="bob.j@example.com", phone_number="0433333333"
        )
        self.motorcycle3 = CustomerMotorcycleFactory(
            service_profile=self.profile3,
            brand="Kawasaki",
            model="Ninja 400",
            year="2019",
            rego="BJ003",
        )
        self.service_type3 = ServiceTypeFactory(
            name="Major Service", description="Full inspection and service"
        )
        self.payment3 = PaymentFactory(status="refunded")
        self.booking3 = ServiceBookingFactory(
            service_booking_reference="SVC-PQRSTU03",
            service_profile=self.profile3,
            customer_motorcycle=self.motorcycle3,
            service_type=self.service_type3,
            dropoff_date=date.today() + timedelta(days=2),
            dropoff_time=time(9, 0),
            booking_status="cancelled",
            payment_status="refunded",
            payment=self.payment3,
            customer_notes="Decided to sell the bike.",
        )

        self.profile4 = ServiceProfileFactory(
            name="Alice Wonderland",
            email="alice.w@example.com",
            phone_number="0444444444",
        )
        self.motorcycle4 = CustomerMotorcycleFactory(
            service_profile=self.profile4,
            brand="Suzuki",
            model="GSX-R1000",
            year="2021",
            rego="AW004",
        )
        self.service_type4 = ServiceTypeFactory(
            name="General Check", description="Pre-purchase inspection"
        )
        self.payment4 = PaymentFactory(status="unpaid", amount=0)
        self.booking4 = ServiceBookingFactory(
            service_booking_reference="SVC-GHIJKL04",
            service_profile=self.profile4,
            customer_motorcycle=self.motorcycle4,
            service_type=self.service_type4,
            dropoff_date=date.today() + timedelta(days=1),
            dropoff_time=time(11, 0),
            booking_status="pending",
            payment_status="unpaid",
            payment=self.payment4,
            customer_notes="",
        )

    def _make_request(self, query_term, user=None):

        url = reverse("service:admin_api_search_bookings")
        if query_term:
            url += f"?query={query_term}"
        request = self.factory.get(url)
        if user:
            request.user = user
        else:
            request.user = self.staff_user
        return search_service_bookings_ajax(request)

    def test_search_by_booking_reference(self):

        response = self._make_request(query_term="ABCDEF01")
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["bookings"]), 1)
        self.assertEqual(
            content["bookings"][0]["reference"], self.booking1.service_booking_reference
        )

        response = self._make_request(query_term="SVC-XYZ")
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["bookings"]), 1)
        self.assertEqual(
            content["bookings"][0]["reference"], self.booking2.service_booking_reference
        )

    def test_search_by_customer_name(self):

        response = self._make_request(query_term="John Doe")
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["bookings"]), 1)
        self.assertEqual(content["bookings"][0]["customer_name"], self.profile1.name)

        response = self._make_request(query_term="Smith")
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["bookings"]), 1)
        self.assertEqual(content["bookings"][0]["customer_name"], self.profile2.name)

    def test_search_by_customer_email(self):

        response = self._make_request(query_term="jane.smith@example.com")
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["bookings"]), 1)
        self.assertEqual(content["bookings"][0]["customer_name"], self.profile2.name)

    def test_search_by_motorcycle_brand_model_year(self):

        response = self._make_request(query_term="Honda")
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["bookings"]), 1)
        self.assertIn("Honda", content["bookings"][0]["motorcycle_info"])

        response = self._make_request(query_term="CBR600RR")
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["bookings"]), 1)
        self.assertIn("CBR600RR", content["bookings"][0]["motorcycle_info"])

        response = self._make_request(query_term="2022")
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["bookings"]), 1)
        self.assertIn("2022", content["bookings"][0]["motorcycle_info"])

        response = self._make_request(query_term="GSX-R1000")
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["bookings"]), 1)
        self.assertIn("Suzuki", content["bookings"][0]["motorcycle_info"])

    def test_search_by_rego(self):

        response = self._make_request(query_term="AW004")
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["bookings"]), 1)
        self.assertEqual(content["bookings"][0]["customer_name"], self.profile4.name)

    def test_search_by_service_type_name_description(self):

        response = self._make_request(query_term="Oil Change")
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["bookings"]), 1)
        self.assertEqual(
            content["bookings"][0]["service_type_name"], self.service_type1.name
        )

        response = self._make_request(query_term="inspection")
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["bookings"]), 2)
        self.assertEqual(
            content["bookings"][0]["service_type_name"], self.service_type3.name
        )
        self.assertEqual(
            content["bookings"][1]["service_type_name"], self.service_type4.name
        )

    def test_search_by_booking_status(self):

        response = self._make_request(query_term="confirmed")
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["bookings"]), 1)
        self.assertEqual(content["bookings"][0]["booking_status"], "Confirmed")

        response = self._make_request(query_term="pending")
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["bookings"]), 2)

    def test_search_by_customer_notes(self):

        response = self._make_request(query_term="synthetic oil")
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["bookings"]), 1)
        self.assertEqual(
            content["bookings"][0]["reference"], self.booking1.service_booking_reference
        )

    def test_search_multiple_matches_and_ordering(self):

        response = self._make_request(query_term="pending")
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["bookings"]), 2)

        self.assertEqual(
            content["bookings"][0]["reference"], self.booking2.service_booking_reference
        )
        self.assertEqual(
            content["bookings"][1]["reference"], self.booking4.service_booking_reference
        )

    def test_search_no_matches(self):

        response = self._make_request(query_term="NonExistentBookingTerm")
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["bookings"]), 0)
        self.assertEqual(content["bookings"], [])

    def test_search_empty_query(self):

        response = self._make_request(query_term="")
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["bookings"]), 0)
        self.assertEqual(content["bookings"], [])

    def test_search_no_query_parameter(self):

        url = reverse("service:admin_api_search_bookings")
        request = self.factory.get(url)
        request.user = self.staff_user
        response = search_service_bookings_ajax(request)

        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertIn("bookings", content)
        self.assertEqual(len(content["bookings"]), 0)
        self.assertEqual(content["bookings"], [])

    def test_only_get_requests_allowed(self):

        url = reverse("service:admin_api_search_bookings")
        request = self.factory.post(url)
        request.user = self.staff_user

        response = search_service_bookings_ajax(request)

        self.assertEqual(response.status_code, 405)

    def test_permission_denied_for_non_staff_user(self):

        response = self._make_request(query_term="John Doe", user=self.non_staff_user)
        self.assertEqual(response.status_code, 403)
        content = json.loads(response.content)
        self.assertIn("error", content)
        self.assertEqual(content["error"], "Permission denied")
