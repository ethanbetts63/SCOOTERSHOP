from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal
import datetime # Import datetime

# Import the form and its constants
from service.forms import (
    PaymentOptionForm,
    PAYMENT_OPTION_DEPOSIT,
    PAYMENT_OPTION_FULL_ONLINE,
    PAYMENT_OPTION_INSTORE
)

# Import the ServiceSettings model and its factory
from service.models import ServiceSettings
from ..test_helpers.model_factories import ServiceSettingsFactory

class PaymentOptionFormTest(TestCase):
    """
    Tests for the PaymentOptionForm (Step 5 form).
    This form dynamically populates payment options based on ServiceSettings.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        We'll create various ServiceSettings configurations.
        """
        # Create a default ServiceSettings instance
        # The factory's _create method ensures only one instance (pk=1) exists
        cls.default_settings = ServiceSettingsFactory(
            enable_deposit=True,
            deposit_calc_method='FLAT_FEE',
            deposit_flat_fee_amount=Decimal('50.00'),
            enable_online_full_payment=True,
            enable_instore_full_payment=True,
            currency_symbol='$'
        )

        # Settings for only deposit enabled
        cls.deposit_only_settings = ServiceSettingsFactory(
            pk=2, # Use a different PK to avoid conflict if factory doesn't strictly enforce singleton
            enable_deposit=True,
            deposit_calc_method='FLAT_FEE',
            deposit_flat_fee_amount=Decimal('25.00'),
            enable_online_full_payment=False,
            enable_instore_full_payment=False,
            currency_symbol='$'
        )

        # Settings for only full online payment enabled
        cls.full_online_only_settings = ServiceSettingsFactory(
            pk=3,
            enable_deposit=False,
            enable_online_full_payment=True,
            enable_instore_full_payment=False,
            currency_symbol='$'
        )

        # Settings for only in-store payment enabled
        cls.instore_only_settings = ServiceSettingsFactory(
            pk=4,
            enable_deposit=False,
            enable_online_full_payment=False,
            enable_instore_full_payment=True,
            currency_symbol='$'
        )

        # Settings for no payment options enabled (should result in no choices)
        cls.no_payment_settings = ServiceSettingsFactory(
            pk=5,
            enable_deposit=False,
            enable_online_full_payment=False,
            enable_instore_full_payment=False,
            currency_symbol='$'
        )

        # Settings for deposit by percentage
        cls.deposit_percentage_settings = ServiceSettingsFactory(
            pk=6,
            enable_deposit=True,
            deposit_calc_method='PERCENTAGE',
            deposit_percentage=Decimal('0.20'), # 20%
            enable_online_full_payment=False,
            enable_instore_full_payment=False,
            currency_symbol='$'
        )


    def test_form_initialization_all_options_enabled(self):
        """
        Test that the form correctly populates choices when all payment options are enabled.
        """
        form = PaymentOptionForm(service_settings=self.default_settings)
        expected_choices = [
            (PAYMENT_OPTION_DEPOSIT, f"Pay Deposit Online (${self.default_settings.deposit_flat_fee_amount:.2f})"),
            (PAYMENT_OPTION_FULL_ONLINE, "Pay Full Amount Online Now"),
            (PAYMENT_OPTION_INSTORE, "Pay In-Store on Drop-off"),
        ]
        self.assertEqual(form.fields['payment_option'].choices, expected_choices)
        self.assertIsNone(form.fields['payment_option'].initial) # No initial selection if multiple choices

    def test_form_initialization_deposit_only(self):
        """
        Test that the form correctly populates choices when only deposit is enabled.
        Also check initial selection.
        """
        form = PaymentOptionForm(service_settings=self.deposit_only_settings)
        expected_choices = [
            (PAYMENT_OPTION_DEPOSIT, f"Pay Deposit Online (${self.deposit_only_settings.deposit_flat_fee_amount:.2f})"),
        ]
        self.assertEqual(form.fields['payment_option'].choices, expected_choices)
        self.assertEqual(form.fields['payment_option'].initial, PAYMENT_OPTION_DEPOSIT) # Should be pre-selected

    def test_form_initialization_full_online_only(self):
        """
        Test that the form correctly populates choices when only full online is enabled.
        Also check initial selection.
        """
        form = PaymentOptionForm(service_settings=self.full_online_only_settings)
        expected_choices = [
            (PAYMENT_OPTION_FULL_ONLINE, "Pay Full Amount Online Now"),
        ]
        self.assertEqual(form.fields['payment_option'].choices, expected_choices)
        self.assertEqual(form.fields['payment_option'].initial, PAYMENT_OPTION_FULL_ONLINE) # Should be pre-selected

    def test_form_initialization_instore_only(self):
        """
        Test that the form correctly populates choices when only in-store is enabled.
        Also check initial selection.
        """
        form = PaymentOptionForm(service_settings=self.instore_only_settings)
        expected_choices = [
            (PAYMENT_OPTION_INSTORE, "Pay In-Store on Drop-off"),
        ]
        self.assertEqual(form.fields['payment_option'].choices, expected_choices)
        self.assertEqual(form.fields['payment_option'].initial, PAYMENT_OPTION_INSTORE) # Should be pre-selected

    def test_form_initialization_no_options_enabled(self):
        """
        Test that the form has no choices when no payment options are enabled.
        """
        form = PaymentOptionForm(service_settings=self.no_payment_settings)
        self.assertEqual(form.fields['payment_option'].choices, [])
        self.assertIsNone(form.fields['payment_option'].initial)

    def test_form_initialization_deposit_percentage_display(self):
        """
        Test that the deposit option displays 'calculated' when method is percentage.
        """
        form = PaymentOptionForm(service_settings=self.deposit_percentage_settings)
        expected_choices = [
            (PAYMENT_OPTION_DEPOSIT, "Pay Deposit Online (calculated)"),
        ]
        self.assertEqual(form.fields['payment_option'].choices, expected_choices)


    def test_form_valid_submission_all_options(self):
        """
        Test a valid submission when all options are available.
        """
        data = {
            'dropoff_date': datetime.date.today(), # Added dropoff_date
            'dropoff_time': datetime.time(9, 0),    # Added dropoff_time
            'payment_option': PAYMENT_OPTION_FULL_ONLINE,
            'service_terms_accepted': True,
        }
        form = PaymentOptionForm(service_settings=self.default_settings, data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data['dropoff_date'], datetime.date.today())
        self.assertEqual(form.cleaned_data['dropoff_time'], datetime.time(9, 0))
        self.assertEqual(form.cleaned_data['payment_option'], PAYMENT_OPTION_FULL_ONLINE)
        self.assertTrue(form.cleaned_data['service_terms_accepted'])

    def test_form_valid_submission_deposit_only(self):
        """
        Test a valid submission when only deposit option is available.
        """
        data = {
            'dropoff_date': datetime.date.today(), # Added dropoff_date
            'dropoff_time': datetime.time(9, 0),    # Added dropoff_time
            'payment_option': PAYMENT_OPTION_DEPOSIT,
            'service_terms_accepted': True,
        }
        form = PaymentOptionForm(service_settings=self.deposit_only_settings, data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data['dropoff_date'], datetime.date.today())
        self.assertEqual(form.cleaned_data['dropoff_time'], datetime.time(9, 0))
        self.assertEqual(form.cleaned_data['payment_option'], PAYMENT_OPTION_DEPOSIT)
        self.assertTrue(form.cleaned_data['service_terms_accepted'])

    def test_form_invalid_submission_no_payment_option_selected(self):
        """
        Test that the form is invalid if no payment option is selected.
        """
        data = {
            'dropoff_date': datetime.date.today(), # Added dropoff_date
            'dropoff_time': datetime.time(9, 0),    # Added dropoff_time
            'payment_option': '', # No option selected
            'service_terms_accepted': True,
        }
        form = PaymentOptionForm(service_settings=self.default_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('payment_option', form.errors)
        self.assertIn('This field is required.', form.errors['payment_option'])

    def test_form_invalid_submission_terms_not_accepted(self):
        """
        Test that the form is invalid if terms are not accepted.
        """
        data = {
            'dropoff_date': datetime.date.today(), # Added dropoff_date
            'dropoff_time': datetime.time(9, 0),    # Added dropoff_time
            'payment_option': PAYMENT_OPTION_FULL_ONLINE,
            'service_terms_accepted': False, # Terms not accepted
        }
        form = PaymentOptionForm(service_settings=self.default_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('service_terms_accepted', form.errors)
        self.assertIn('This field is required.', form.errors['service_terms_accepted'])

    def test_form_invalid_submission_invalid_choice(self):
        """
        Test that the form is invalid if an invalid payment option is submitted
        (i.e., one not available based on settings).
        """
        data = {
            'dropoff_date': datetime.date.today(), # Added dropoff_date
            'dropoff_time': datetime.time(9, 0),    # Added dropoff_time
            'payment_option': PAYMENT_OPTION_FULL_ONLINE, # This option is NOT enabled in deposit_only_settings
            'service_terms_accepted': True,
        }
        form = PaymentOptionForm(service_settings=self.deposit_only_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('payment_option', form.errors)
        self.assertIn(f"Select a valid choice. {PAYMENT_OPTION_FULL_ONLINE} is not one of the available choices.", form.errors['payment_option'])

    def test_form_invalid_submission_no_choices_available(self):
        """
        Test that the form is invalid if no choices are available and a selection is attempted.
        """
        data = {
            'dropoff_date': datetime.date.today(), # Added dropoff_date
            'dropoff_time': datetime.time(9, 0),    # Added dropoff_time
            'payment_option': PAYMENT_OPTION_DEPOSIT,
            'service_terms_accepted': True,
        }
        form = PaymentOptionForm(service_settings=self.no_payment_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('payment_option', form.errors)
        self.assertIn(f"Select a valid choice. {PAYMENT_OPTION_DEPOSIT} is not one of the available choices.", form.errors['payment_option'])
