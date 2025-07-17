from django.test import TestCase, RequestFactory
from django.urls import reverse
import datetime
import uuid
from unittest.mock import patch


from service.views.user_views.step2_motorcycle_selection_view import (
    Step2MotorcycleSelectionView,
)
from service.forms import MotorcycleSelectionForm, ADD_NEW_MOTORCYCLE_OPTION


from service.models import TempServiceBooking, CustomerMotorcycle
from users.tests.test_helpers.model_factories import UserFactory
from service.tests.test_helpers.model_factories import TempServiceBookingFactory, ServiceProfileFactory, ServiceTypeFactory, CustomerMotorcycleFactory



class Step2MotorcycleSelectionViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.factory = RequestFactory()
        cls.user = UserFactory()
        cls.service_profile = ServiceProfileFactory(user=cls.user)
        cls.service_type = ServiceTypeFactory()
        cls.base_url = reverse("service:service_book_step2")

    def setUp(self):

        TempServiceBooking.objects.all().delete()
        CustomerMotorcycle.objects.all().delete()

        self.client.force_login(self.user)

        self.temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            service_date=datetime.date.today() + datetime.timedelta(days=7),
            customer_motorcycle=None,
        )

        session = self.client.session
        session["temp_service_booking_uuid"] = str(self.temp_booking.session_uuid)
        session.save()

        self.customer_motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile
        )

    def test_dispatch_no_temp_booking_uuid_in_session(self):

        request = self.factory.get(self.base_url)
        request.session = {}
        request.user = self.user
        response = Step2MotorcycleSelectionView().dispatch(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("service:service"))

    def test_dispatch_invalid_temp_booking_uuid_in_session(self):

        request = self.factory.get(self.base_url)

        request.session = {"temp_service_booking_uuid": str(uuid.uuid4())}
        request.user = self.user
        response = Step2MotorcycleSelectionView().dispatch(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("service:service"))

        self.assertNotIn("temp_service_booking_uuid", request.session)

    def test_dispatch_temp_booking_missing_service_profile(self):

        self.temp_booking.service_profile = None
        self.temp_booking.save()
        request = self.factory.get(self.base_url)

        request.session = {
            "temp_service_booking_uuid": str(self.temp_booking.session_uuid)
        }
        request.user = self.user
        response = Step2MotorcycleSelectionView().dispatch(request)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(response.url, reverse("service:service_book_step3"))

    def test_dispatch_no_motorcycles_redirects_to_step3(self):

        CustomerMotorcycle.objects.all().delete()
        request = self.factory.get(self.base_url)

        request.session = {
            "temp_service_booking_uuid": str(self.temp_booking.session_uuid)
        }
        request.user = self.user
        response = Step2MotorcycleSelectionView().dispatch(request)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(response.url, reverse("service:service_book_step3"))

    def test_get_renders_form_with_motorcycles(self):

        CustomerMotorcycleFactory(service_profile=self.service_profile)

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "service/step2_motorcycle_selection.html")
        self.assertIsInstance(response.context["form"], MotorcycleSelectionForm)
        self.assertEqual(response.context["temp_booking"], self.temp_booking)

        form_choices = [
            choice[0]
            for choice in response.context["form"].fields["selected_motorcycle"].choices
        ]
        self.assertIn(str(self.customer_motorcycle.pk), form_choices)
        self.assertIn(ADD_NEW_MOTORCYCLE_OPTION, form_choices)

    @patch(
        "service.views.user_views.step2_motorcycle_selection_view.MotorcycleSelectionForm"
    )
    def test_post_select_new_motorcycle_redirects_to_step3(
        self, MockMotorcycleSelectionForm
    ):

        mock_form_instance = MockMotorcycleSelectionForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            "selected_motorcycle": ADD_NEW_MOTORCYCLE_OPTION
        }

        response = self.client.post(
            self.base_url, {"selected_motorcycle": ADD_NEW_MOTORCYCLE_OPTION}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("service:service_book_step3"))

        self.temp_booking.refresh_from_db()
        self.assertIsNone(self.temp_booking.customer_motorcycle)

        MockMotorcycleSelectionForm.assert_called_once()

    @patch(
        "service.views.user_views.step2_motorcycle_selection_view.MotorcycleSelectionForm"
    )
    def test_post_select_existing_motorcycle_redirects_to_step4(
        self, MockMotorcycleSelectionForm
    ):

        mock_form_instance = MockMotorcycleSelectionForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            "selected_motorcycle": str(self.customer_motorcycle.pk)
        }

        response = self.client.post(
            self.base_url, {"selected_motorcycle": str(self.customer_motorcycle.pk)}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("service:service_book_step4"))

        self.temp_booking.refresh_from_db()
        self.assertEqual(
            self.temp_booking.customer_motorcycle, self.customer_motorcycle
        )
        MockMotorcycleSelectionForm.assert_called_once()

    @patch(
        "service.views.user_views.step2_motorcycle_selection_view.MotorcycleSelectionForm"
    )
    def test_post_invalid_motorcycle_selection_renders_form_with_error(
        self, MockMotorcycleSelectionForm
    ):

        mock_form_instance = MockMotorcycleSelectionForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {"selected_motorcycle": "9999"}

        mock_form_instance.errors = {
            "selected_motorcycle": ["Invalid motorcycle selection."]
        }

        with patch(
            "service.views.user_views.step2_motorcycle_selection_view.get_object_or_404",
            side_effect=CustomerMotorcycle.DoesNotExist,
        ):
            response = self.client.post(self.base_url, {"selected_motorcycle": "9999"})
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "service/step2_motorcycle_selection.html")
            self.assertIn("form", response.context)

            self.assertIn("selected_motorcycle", response.context["form"].errors)
            self.assertIn(
                "Invalid motorcycle selection.",
                response.context["form"].errors["selected_motorcycle"],
            )

            self.temp_booking.refresh_from_db()
            self.assertIsNone(self.temp_booking.customer_motorcycle)
        MockMotorcycleSelectionForm.assert_called_once()

    @patch(
        "service.views.user_views.step2_motorcycle_selection_view.MotorcycleSelectionForm"
    )
    def test_post_form_not_valid_renders_form_with_errors(
        self, MockMotorcycleSelectionForm
    ):

        mock_form_instance = MockMotorcycleSelectionForm.return_value
        mock_form_instance.is_valid.return_value = False

        mock_form_instance.errors = {"selected_motorcycle": ["This field is required."]}

        response = self.client.post(self.base_url, {})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "service/step2_motorcycle_selection.html")
        self.assertIn("form", response.context)

        self.assertIn("selected_motorcycle", response.context["form"].errors)
        self.assertIn(
            "This field is required.",
            response.context["form"].errors["selected_motorcycle"],
        )

        self.temp_booking.refresh_from_db()
        self.assertIsNone(self.temp_booking.customer_motorcycle)
        MockMotorcycleSelectionForm.assert_called_once()

    def test_post_authenticated_user_without_motorcycles_still_redirects_to_step3(self):

        CustomerMotorcycle.objects.all().delete()

        response = self.client.post(
            self.base_url, {"selected_motorcycle": ADD_NEW_MOTORCYCLE_OPTION}
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("service:service_book_step3"))
        self.temp_booking.refresh_from_db()
        self.assertIsNone(self.temp_booking.customer_motorcycle)
