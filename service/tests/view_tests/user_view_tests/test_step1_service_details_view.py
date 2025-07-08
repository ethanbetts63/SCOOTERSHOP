from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.messages import get_messages

from django.contrib.messages.storage.fallback import FallbackStorage
import datetime
from unittest.mock import patch, Mock


from service.views.user_views.step1_service_details_view import Step1ServiceDetailsView


from service.models import (
    TempServiceBooking,
    ServiceSettings,
    BlockedServiceDate,
    CustomerMotorcycle,
)

from ...test_helpers.model_factories import (
    ServiceSettingsFactory,
    ServiceTypeFactory,
    TempServiceBookingFactory,
    BlockedServiceDateFactory,
    UserFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
)


class Step1ServiceDetailsViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()

        cls.user = UserFactory()
        cls.service_profile = ServiceProfileFactory(user=cls.user)
        cls.service_type = ServiceTypeFactory()

        cls.fixed_now = datetime.datetime(
            2025, 6, 15, 10, 0, 0, tzinfo=datetime.timezone.utc
        )
        cls.fixed_local_date = datetime.date(2025, 6, 15)

        cls.patcher_now = patch("django.utils.timezone.now", return_value=cls.fixed_now)
        cls.patcher_localtime = patch(
            "django.utils.timezone.localtime", return_value=cls.fixed_now
        )

        cls.mock_now = cls.patcher_now.start()
        cls.mock_localtime = cls.patcher_localtime.start()

    @classmethod
    def tearDownClass(cls):
        cls.patcher_now.stop()
        cls.patcher_localtime.stop()
        super().tearDownClass()

    def setUp(self):
        ServiceSettings.objects.all().delete()
        TempServiceBooking.objects.all().delete()
        BlockedServiceDate.objects.all().delete()
        CustomerMotorcycle.objects.all().delete()

        self.service_settings = ServiceSettingsFactory(
            booking_advance_notice=1,
            booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun",
        )

        self.request = self.factory.post(reverse("core:index"), {})
        self.request.session = {}
        setattr(self.request, "_messages", FallbackStorage(self.request))
        setattr(self.request, "_get_messages", lambda: FallbackStorage(self.request))

        self.request.user = Mock(is_authenticated=False)

    @patch("service.views.user_views.step1_service_details_view.ServiceDetailsForm")
    def test_invalid_form_submission(self, MockServiceDetailsForm):
        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = False
        mock_form_instance.errors = {"service_type": ["This field is required."]}

        response = Step1ServiceDetailsView().post(self.request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("core:index"))

        messages = list(get_messages(self.request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Error in service_type: This field is required."
        )
        MockServiceDetailsForm.assert_called_once_with(self.request.POST)
        self.assertEqual(TempServiceBooking.objects.count(), 0)

    @patch("service.views.user_views.step1_service_details_view.ServiceDetailsForm")
    def test_service_date_too_early(self, MockServiceDetailsForm):
        self.service_settings.booking_advance_notice = 1
        self.service_settings.save()

        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            "service_type": self.service_type,
            "service_date": self.fixed_local_date,
        }

        self.request.user = Mock(is_authenticated=True)
        response = Step1ServiceDetailsView().post(self.request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("core:index"))

        messages = list(get_messages(self.request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "Service date must be at least 1 days from now. Please choose a later date.",
        )
        self.assertEqual(TempServiceBooking.objects.count(), 0)

    @patch("service.views.user_views.step1_service_details_view.ServiceDetailsForm")
    def test_service_date_on_closed_day(self, MockServiceDetailsForm):
        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri"
        self.service_settings.booking_advance_notice = 0
        self.service_settings.save()

        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            "service_type": self.service_type,
            "service_date": self.fixed_local_date,
        }

        self.request.user = Mock(is_authenticated=True)
        response = Step1ServiceDetailsView().post(self.request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("core:index"))

        messages = list(get_messages(self.request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Services are not available on Sundays.")
        self.assertEqual(TempServiceBooking.objects.count(), 0)

    @patch("service.views.user_views.step1_service_details_view.ServiceDetailsForm")
    def test_service_date_blocked(self, MockServiceDetailsForm):
        blocked_date = self.fixed_local_date + datetime.timedelta(days=2)
        BlockedServiceDateFactory(start_date=blocked_date, end_date=blocked_date)

        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            "service_type": self.service_type,
            "service_date": blocked_date,
        }

        self.request.user = Mock(is_authenticated=True)
        response = Step1ServiceDetailsView().post(self.request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("core:index"))

        messages = list(get_messages(self.request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "Selected service date overlaps with a blocked service period.",
        )
        self.assertEqual(TempServiceBooking.objects.count(), 0)

    @patch("service.views.user_views.step1_service_details_view.ServiceDetailsForm")
    @patch(
        "service.views.user_views.step1_service_details_view.reverse",
        side_effect=lambda *args, **kwargs: {
            "service:service_book_step2": "/service-book/step2/",
            "service:service_book_step3": "/service-book/step3/",
            "core:index": "/index/",
        }.get(args[0], reverse(*args, **kwargs)),
    )
    def test_new_temp_booking_anonymous_no_motorcycles_redirect_step3(
        self, mock_reverse, MockServiceDetailsForm
    ):
        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            "service_type": self.service_type,
            "service_date": self.fixed_local_date + datetime.timedelta(days=2),
        }

        self.request.session = {}
        self.request.user = Mock(is_authenticated=False)

        response = Step1ServiceDetailsView().post(self.request)

        self.assertEqual(response.status_code, 302)

        self.assertTrue(response.url.startswith("/service-book/step3/"))

        messages = list(get_messages(self.request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Service details selected. Please choose your motorcycle."
        )

        temp_booking = TempServiceBooking.objects.get()
        self.assertEqual(temp_booking.service_type, self.service_type)
        self.assertEqual(
            temp_booking.service_date, mock_form_instance.cleaned_data["service_date"]
        )
        self.assertIsNone(temp_booking.service_profile)

        self.assertIn("temp_service_booking_uuid", self.request.session)
        self.assertEqual(
            str(temp_booking.session_uuid),
            self.request.session["temp_service_booking_uuid"],
        )

    @patch("service.views.user_views.step1_service_details_view.ServiceDetailsForm")
    @patch(
        "service.views.user_views.step1_service_details_view.reverse",
        side_effect=lambda *args, **kwargs: {
            "service:service_book_step2": "/service-book/step2/",
            "service:service_book_step3": "/service-book/step3/",
            "core:index": "/index/",
        }.get(args[0], reverse(*args, **kwargs)),
    )
    def test_new_temp_booking_authenticated_no_motorcycles_redirect_step3(
        self, mock_reverse, MockServiceDetailsForm
    ):
        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            "service_type": self.service_type,
            "service_date": self.fixed_local_date + datetime.timedelta(days=2),
        }

        self.request.session = {}
        self.request.user = self.user

        response = Step1ServiceDetailsView().post(self.request)

        self.assertEqual(response.status_code, 302)

        self.assertTrue(response.url.startswith("/service-book/step3/"))

        messages = list(get_messages(self.request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Service details selected. Please choose your motorcycle."
        )

        temp_booking = TempServiceBooking.objects.get()
        self.assertEqual(temp_booking.service_type, self.service_type)
        self.assertEqual(
            temp_booking.service_date, mock_form_instance.cleaned_data["service_date"]
        )
        self.assertEqual(temp_booking.service_profile, self.service_profile)

        self.assertIn("temp_service_booking_uuid", self.request.session)
        self.assertEqual(
            str(temp_booking.session_uuid),
            self.request.session["temp_service_booking_uuid"],
        )

    @patch("service.views.user_views.step1_service_details_view.ServiceDetailsForm")
    @patch(
        "service.views.user_views.step1_service_details_view.reverse",
        side_effect=lambda *args, **kwargs: {
            "service:service_book_step2": "/service-book/step2/",
            "service:service_book_step3": "/service-book/step3/",
            "core:index": "/index/",
        }.get(args[0], reverse(*args, **kwargs)),
    )
    def test_new_temp_booking_authenticated_with_motorcycles_redirect_step2(
        self, mock_reverse, MockServiceDetailsForm
    ):
        CustomerMotorcycleFactory(service_profile=self.service_profile)

        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            "service_type": self.service_type,
            "service_date": self.fixed_local_date + datetime.timedelta(days=2),
        }

        self.request.session = {}
        self.request.user = self.user

        response = Step1ServiceDetailsView().post(self.request)

        self.assertEqual(response.status_code, 302)

        self.assertTrue(response.url.startswith("/service-book/step2/"))

        messages = list(get_messages(self.request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Service details selected. Please choose your motorcycle."
        )

        temp_booking = TempServiceBooking.objects.get()
        self.assertEqual(temp_booking.service_type, self.service_type)
        self.assertEqual(
            temp_booking.service_date, mock_form_instance.cleaned_data["service_date"]
        )
        self.assertEqual(temp_booking.service_profile, self.service_profile)

        self.assertIn("temp_service_booking_uuid", self.request.session)
        self.assertEqual(
            str(temp_booking.session_uuid),
            self.request.session["temp_service_booking_uuid"],
        )

    @patch("service.views.user_views.step1_service_details_view.ServiceDetailsForm")
    @patch(
        "service.views.user_views.step1_service_details_view.reverse",
        side_effect=lambda *args, **kwargs: {
            "service:service_book_step2": "/service-book/step2/",
            "service:service_book_step3": "/service-book/step3/",
            "core:index": "/index/",
        }.get(args[0], reverse(*args, **kwargs)),
    )
    def test_update_existing_temp_booking(self, mock_reverse, MockServiceDetailsForm):
        existing_temp_booking = TempServiceBookingFactory(
            service_type=ServiceTypeFactory(),
            service_date=self.fixed_local_date + datetime.timedelta(days=5),
            service_profile=self.service_profile,
        )

        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            "service_type": self.service_type,
            "service_date": self.fixed_local_date + datetime.timedelta(days=2),
        }

        self.request.session = {
            "temp_service_booking_uuid": str(existing_temp_booking.session_uuid)
        }
        self.request.user = self.user
        CustomerMotorcycleFactory(service_profile=self.service_profile)

        response = Step1ServiceDetailsView().post(self.request)

        self.assertEqual(response.status_code, 302)

        self.assertTrue(response.url.startswith("/service-book/step2/"))

        messages = list(get_messages(self.request))
        self.assertEqual(len(messages), 1)

        self.assertEqual(
            str(messages[0]), "Service details updated. Please choose your motorcycle."
        )

        self.assertEqual(TempServiceBooking.objects.count(), 1)
        updated_temp_booking = TempServiceBooking.objects.get(
            session_uuid=existing_temp_booking.session_uuid
        )
        self.assertEqual(updated_temp_booking.service_type, self.service_type)
        self.assertEqual(
            updated_temp_booking.service_date,
            mock_form_instance.cleaned_data["service_date"],
        )
        self.assertEqual(updated_temp_booking.service_profile, self.service_profile)

    @patch("service.views.user_views.step1_service_details_view.ServiceDetailsForm")
    def test_exception_during_save(self, MockServiceDetailsForm):
        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            "service_type": self.service_type,
            "service_date": self.fixed_local_date + datetime.timedelta(days=2),
        }

        with patch(
            "service.views.user_views.step1_service_details_view.TempServiceBooking.objects.create",
            side_effect=Exception("Database error!"),
        ):

            self.request.session = {}
            self.request.user = Mock(is_authenticated=False)

            response = Step1ServiceDetailsView().post(self.request)

            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse("core:index"))

            messages = list(get_messages(self.request))
            self.assertEqual(len(messages), 1)
            self.assertTrue(
                "An unexpected error occurred while saving your selection"
                in str(messages[0])
            )
            self.assertEqual(TempServiceBooking.objects.count(), 0)

    @patch("service.views.user_views.step1_service_details_view.ServiceDetailsForm")
    def test_session_reference_cleared(self, MockServiceDetailsForm):
        mock_form_instance = MockServiceDetailsForm.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            "service_type": self.service_type,
            "service_date": self.fixed_local_date + datetime.timedelta(days=2),
        }

        existing_temp_booking_for_test = TempServiceBookingFactory(
            service_type=self.service_type,
            service_date=self.fixed_local_date + datetime.timedelta(days=1),
            service_profile=self.service_profile,
        )

        self.request.session = {
            "service_booking_reference": "OLDREF123",
            "temp_service_booking_uuid": str(
                existing_temp_booking_for_test.session_uuid
            ),
        }
        self.request.user = self.user
        CustomerMotorcycleFactory(service_profile=self.service_profile)

        response = Step1ServiceDetailsView().post(self.request)

        self.assertNotIn("service_booking_reference", self.request.session)

        self.assertIn("temp_service_booking_uuid", self.request.session)
        self.assertEqual(
            str(existing_temp_booking_for_test.session_uuid),
            self.request.session["temp_service_booking_uuid"],
        )
