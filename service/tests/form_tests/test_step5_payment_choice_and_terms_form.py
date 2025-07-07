from django.test import TestCase
from decimal import Decimal
import datetime


from service.forms import (
    PaymentOptionForm,
    PAYMENT_OPTION_DEPOSIT,
    PAYMENT_OPTION_FULL_ONLINE,
    PAYMENT_OPTION_INSTORE,
)
from ..test_helpers.model_factories import (
    ServiceSettingsFactory,
    TempServiceBookingFactory,
)


class PaymentOptionFormTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.default_settings = ServiceSettingsFactory(
            enable_online_deposit=True,
            deposit_calc_method="FLAT_FEE",
            deposit_flat_fee_amount=Decimal("50.00"),
            enable_online_full_payment=True,
            enable_instore_full_payment=True,
            currency_symbol="$",
        )

        cls.deposit_only_settings = ServiceSettingsFactory(
            pk=2,
            enable_online_deposit=True,
            deposit_calc_method="FLAT_FEE",
            deposit_flat_fee_amount=Decimal("25.00"),
            enable_online_full_payment=False,
            enable_instore_full_payment=False,
            currency_symbol="$",
        )

        cls.full_online_only_settings = ServiceSettingsFactory(
            pk=3,
            enable_online_deposit=False,
            enable_online_full_payment=True,
            enable_instore_full_payment=False,
            currency_symbol="$",
        )

        cls.instore_only_settings = ServiceSettingsFactory(
            pk=4,
            enable_online_deposit=False,
            enable_online_full_payment=False,
            enable_instore_full_payment=True,
            currency_symbol="$",
        )

        cls.no_payment_settings = ServiceSettingsFactory(
            pk=5,
            enable_online_deposit=False,
            enable_online_full_payment=False,
            enable_instore_full_payment=False,
            currency_symbol="$",
        )

        cls.deposit_percentage_settings = ServiceSettingsFactory(
            pk=6,
            enable_online_deposit=True,
            deposit_calc_method="PERCENTAGE",
            deposit_percentage=Decimal("0.20"),
            enable_online_full_payment=False,
            enable_instore_full_payment=False,
            currency_symbol="$",
        )

        cls.temp_booking = TempServiceBookingFactory(
            service_date=datetime.date.today() + datetime.timedelta(days=7),
            dropoff_date=datetime.date.today() + datetime.timedelta(days=1),
            dropoff_time=datetime.time(9, 0),
        )

    def test_form_initialization_all_options_enabled(self):

        form = PaymentOptionForm(
            service_settings=self.default_settings, temp_booking=self.temp_booking
        )
        expected_choices = [
            (
                PAYMENT_OPTION_DEPOSIT,
                f"Pay Deposit Online (${self.default_settings.deposit_flat_fee_amount:.2f})",
            ),
            (PAYMENT_OPTION_FULL_ONLINE, "Pay Full Amount Online Now"),
            (PAYMENT_OPTION_INSTORE, "Pay In-Store on Drop-off"),
        ]
        self.assertEqual(form.fields["payment_method"].choices, expected_choices)
        self.assertIsNone(form.fields["payment_method"].initial)

    def test_form_initialization_deposit_only(self):

        form = PaymentOptionForm(
            service_settings=self.deposit_only_settings, temp_booking=self.temp_booking
        )
        expected_choices = [
            (
                PAYMENT_OPTION_DEPOSIT,
                f"Pay Deposit Online (${self.deposit_only_settings.deposit_flat_fee_amount:.2f})",
            ),
        ]
        self.assertEqual(form.fields["payment_method"].choices, expected_choices)
        self.assertEqual(form.fields["payment_method"].initial, PAYMENT_OPTION_DEPOSIT)

    def test_form_initialization_full_online_only(self):

        form = PaymentOptionForm(
            service_settings=self.full_online_only_settings,
            temp_booking=self.temp_booking,
        )
        expected_choices = [
            (PAYMENT_OPTION_FULL_ONLINE, "Pay Full Amount Online Now"),
        ]
        self.assertEqual(form.fields["payment_method"].choices, expected_choices)
        self.assertEqual(
            form.fields["payment_method"].initial, PAYMENT_OPTION_FULL_ONLINE
        )

    def test_form_initialization_instore_only(self):

        form = PaymentOptionForm(
            service_settings=self.instore_only_settings, temp_booking=self.temp_booking
        )
        expected_choices = [
            (PAYMENT_OPTION_INSTORE, "Pay In-Store on Drop-off"),
        ]
        self.assertEqual(form.fields["payment_method"].choices, expected_choices)
        self.assertEqual(form.fields["payment_method"].initial, PAYMENT_OPTION_INSTORE)

    def test_form_initialization_no_options_enabled(self):

        form = PaymentOptionForm(
            service_settings=self.no_payment_settings, temp_booking=self.temp_booking
        )
        self.assertEqual(form.fields["payment_method"].choices, [])
        self.assertIsNone(form.fields["payment_method"].initial)

    def test_form_initialization_deposit_percentage_display(self):

        form = PaymentOptionForm(
            service_settings=self.deposit_percentage_settings,
            temp_booking=self.temp_booking,
        )

        expected_percentage = self.deposit_percentage_settings.deposit_percentage * 100
        expected_display = f"Pay Deposit Online ({expected_percentage:.0f}%)"

        expected_choices = [
            (PAYMENT_OPTION_DEPOSIT, expected_display),
        ]
        self.assertEqual(form.fields["payment_method"].choices, expected_choices)

    def test_form_valid_submission_all_options(self):

        data = {
            "dropoff_date": datetime.date.today() + datetime.timedelta(days=1),
            "dropoff_time": datetime.time(9, 0),
            "payment_method": PAYMENT_OPTION_FULL_ONLINE,
            "service_terms_accepted": True,
        }
        form = PaymentOptionForm(
            service_settings=self.default_settings,
            data=data,
            temp_booking=self.temp_booking,
        )
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(
            form.cleaned_data["dropoff_date"],
            datetime.date.today() + datetime.timedelta(days=1),
        )
        self.assertEqual(form.cleaned_data["dropoff_time"], datetime.time(9, 0))
        self.assertEqual(
            form.cleaned_data["payment_method"], PAYMENT_OPTION_FULL_ONLINE
        )
        self.assertTrue(form.cleaned_data["service_terms_accepted"])

    def test_form_valid_submission_deposit_only(self):

        data = {
            "dropoff_date": datetime.date.today() + datetime.timedelta(days=1),
            "dropoff_time": datetime.time(9, 0),
            "payment_method": PAYMENT_OPTION_DEPOSIT,
            "service_terms_accepted": True,
        }
        form = PaymentOptionForm(
            service_settings=self.deposit_only_settings,
            data=data,
            temp_booking=self.temp_booking,
        )
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(
            form.cleaned_data["dropoff_date"],
            datetime.date.today() + datetime.timedelta(days=1),
        )
        self.assertEqual(form.cleaned_data["dropoff_time"], datetime.time(9, 0))
        self.assertEqual(form.cleaned_data["payment_method"], PAYMENT_OPTION_DEPOSIT)
        self.assertTrue(form.cleaned_data["service_terms_accepted"])

    def test_form_invalid_submission_no_payment_method_selected(self):

        data = {
            "dropoff_date": datetime.date.today() + datetime.timedelta(days=1),
            "dropoff_time": datetime.time(9, 0),
            "payment_method": "",
            "service_terms_accepted": True,
        }
        form = PaymentOptionForm(
            service_settings=self.default_settings,
            data=data,
            temp_booking=self.temp_booking,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("payment_method", form.errors)
        self.assertIn("This field is required.", form.errors["payment_method"])

    def test_form_invalid_submission_terms_not_accepted(self):

        data = {
            "dropoff_date": datetime.date.today() + datetime.timedelta(days=1),
            "dropoff_time": datetime.time(9, 0),
            "payment_method": PAYMENT_OPTION_FULL_ONLINE,
            "service_terms_accepted": False,
        }
        form = PaymentOptionForm(
            service_settings=self.default_settings,
            data=data,
            temp_booking=self.temp_booking,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("service_terms_accepted", form.errors)
        self.assertIn("This field is required.", form.errors["service_terms_accepted"])

    def test_form_invalid_submission_invalid_choice(self):

        data = {
            "dropoff_date": datetime.date.today() + datetime.timedelta(days=1),
            "dropoff_time": datetime.time(9, 0),
            "payment_method": PAYMENT_OPTION_FULL_ONLINE,
            "service_terms_accepted": True,
        }
        form = PaymentOptionForm(
            service_settings=self.deposit_only_settings,
            data=data,
            temp_booking=self.temp_booking,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("payment_method", form.errors)
        self.assertIn(
            f"Select a valid choice. {PAYMENT_OPTION_FULL_ONLINE} is not one of the available choices.",
            form.errors["payment_method"],
        )

    def test_form_invalid_submission_no_choices_available(self):

        data = {
            "dropoff_date": datetime.date.today() + datetime.timedelta(days=1),
            "dropoff_time": datetime.time(9, 0),
            "payment_method": PAYMENT_OPTION_DEPOSIT,
            "service_terms_accepted": True,
        }
        form = PaymentOptionForm(
            service_settings=self.no_payment_settings,
            data=data,
            temp_booking=self.temp_booking,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("payment_method", form.errors)
        self.assertIn(
            f"Select a valid choice. {PAYMENT_OPTION_DEPOSIT} is not one of the available choices.",
            form.errors["payment_method"],
        )
