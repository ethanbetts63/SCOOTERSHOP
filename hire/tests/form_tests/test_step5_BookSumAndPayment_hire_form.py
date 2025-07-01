                                                                 

from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal

from hire.forms.step5_BookSumAndPaymentOptions_form import PaymentOptionForm
from dashboard.models import HireSettings                      
from hire.models import TempHireBooking                      
from hire.tests.test_helpers.model_factories import create_hire_settings, create_temp_hire_booking

class PaymentOptionFormTests(TestCase):
    """
    Tests for the PaymentOptionForm, focusing on its dynamic choice setting
    and clean method.
    """

    def setUp(self):
        """
        Set up common HireSettings and TempHireBooking instances for tests.
        """
                                                             
        HireSettings.objects.all().delete()

                                                            
        self.default_hire_settings = create_hire_settings(
            enable_online_full_payment=False,
            enable_online_deposit_payment=False,
            enable_in_store_full_payment=False,
            deposit_enabled=False,
        )
        self.temp_booking_positive_total = create_temp_hire_booking(grand_total=Decimal('150.00'))
        self.temp_booking_zero_total = create_temp_hire_booking(grand_total=Decimal('0.00'))


                                                              

    def test_init_no_payment_options_enabled(self):
        """
        Test that no choices are set when all payment options are disabled.
        """
        form = PaymentOptionForm(
            temp_booking=self.temp_booking_positive_total,
            hire_settings=self.default_hire_settings
        )
        self.assertEqual(form.fields['payment_method'].choices, [])
        self.assertFalse(form.fields['payment_method'].required)                                       

    def test_init_online_full_payment_enabled(self):
        """
        Test that 'online_full' choice is set when only online full payment is enabled.
        """
        settings = create_hire_settings(enable_online_full_payment=True)
        form = PaymentOptionForm(
            temp_booking=self.temp_booking_positive_total,
            hire_settings=settings
        )
        expected_choices = [('online_full', 'Pay Full Amount Online Now')]
        self.assertEqual(form.fields['payment_method'].choices, expected_choices)
        self.assertTrue(form.fields['payment_method'].required)

    def test_init_in_store_full_payment_enabled(self):
        """
        Test that 'in_store_full' choice is set when only in-store full payment is enabled.
        """
        settings = create_hire_settings(enable_in_store_full_payment=True)
        form = PaymentOptionForm(
            temp_booking=self.temp_booking_positive_total,
            hire_settings=settings
        )
        expected_choices = [('in_store_full', 'Pay Full Amount In-Store at Pickup')]
        self.assertEqual(form.fields['payment_method'].choices, expected_choices)
        self.assertTrue(form.fields['payment_method'].required)

    def test_init_online_deposit_percentage_enabled_positive_total(self):
        """
        Test online deposit choice with percentage method and positive grand total.
        """
        settings = create_hire_settings(
            enable_online_deposit_payment=True,
            deposit_enabled=True,
            default_deposit_calculation_method='percentage',
            deposit_percentage=Decimal('20.00')                  
        )
        form = PaymentOptionForm(
            temp_booking=self.temp_booking_positive_total,                    
            hire_settings=settings
        )
        expected_deposit_amount = Decimal('30.00')
        expected_choices = [
            ('online_deposit', f'Pay Deposit Online Now ({settings.currency_symbol}{expected_deposit_amount:.2f} due now, remaining at pickup)')
        ]
        self.assertEqual(form.fields['payment_method'].choices, expected_choices)
        self.assertTrue(form.fields['payment_method'].required)

    def test_init_online_deposit_fixed_amount_enabled_positive_total(self):
        """
        Test online deposit choice with fixed amount method and positive grand total.
        """
        settings = create_hire_settings(
            enable_online_deposit_payment=True,
            deposit_enabled=True,
            default_deposit_calculation_method='fixed',
            deposit_amount=Decimal('50.00')
        )
        form = PaymentOptionForm(
            temp_booking=self.temp_booking_positive_total,                    
            hire_settings=settings
        )
        expected_deposit_amount = Decimal('50.00')
        expected_choices = [
            ('online_deposit', f'Pay Deposit Online Now ({settings.currency_symbol}{expected_deposit_amount:.2f} due now, remaining at pickup)')
        ]
        self.assertEqual(form.fields['payment_method'].choices, expected_choices)
        self.assertTrue(form.fields['payment_method'].required)

    def test_init_online_deposit_enabled_zero_total(self):
        """
        Test that online deposit choice is NOT set when grand_total is 0.
        """
        settings = create_hire_settings(
            enable_online_deposit_payment=True,
            deposit_enabled=True,
            default_deposit_calculation_method='percentage',
            deposit_percentage=Decimal('20.00')
        )
        form = PaymentOptionForm(
            temp_booking=self.temp_booking_zero_total,                  
            hire_settings=settings
        )
        self.assertEqual(form.fields['payment_method'].choices, [])
        self.assertFalse(form.fields['payment_method'].required)

    def test_init_online_deposit_enabled_deposit_more_than_grand_total(self):
        """
        Test that the deposit amount is capped at grand_total if calculated deposit
        is higher than grand_total.
        """
        settings = create_hire_settings(
            enable_online_deposit_payment=True,
            deposit_enabled=True,
            default_deposit_calculation_method='fixed',
            deposit_amount=Decimal('200.00')                               
        )
        form = PaymentOptionForm(
            temp_booking=self.temp_booking_positive_total,                    
            hire_settings=settings
        )
        expected_deposit_amount = Decimal('150.00')                                  
        expected_choices = [
            ('online_deposit', f'Pay Deposit Online Now ({settings.currency_symbol}{expected_deposit_amount:.2f} due now, remaining at pickup)')
        ]
        self.assertEqual(form.fields['payment_method'].choices, expected_choices)
        self.assertTrue(form.fields['payment_method'].required)

    def test_init_all_payment_options_enabled(self):
        """
        Test that all enabled payment options are set as choices.
        """
        settings = create_hire_settings(
            enable_online_full_payment=True,
            enable_online_deposit_payment=True,
            enable_in_store_full_payment=True,
            deposit_enabled=True,
            default_deposit_calculation_method='fixed',
            deposit_amount=Decimal('50.00')
        )
        form = PaymentOptionForm(
            temp_booking=self.temp_booking_positive_total,
            hire_settings=settings
        )
        expected_choices = [
            ('online_full', 'Pay Full Amount Online Now'),
            ('online_deposit', f'Pay Deposit Online Now ({settings.currency_symbol}{Decimal("50.00"):.2f} due now, remaining at pickup)'),
            ('in_store_full', 'Pay Full Amount In-Store at Pickup')
        ]
        self.assertEqual(form.fields['payment_method'].choices, expected_choices)
        self.assertTrue(form.fields['payment_method'].required)


                                

    def test_clean_valid_selection(self):
        """
        Test that the form is valid when a valid payment method is selected.
        """
        settings = create_hire_settings(enable_online_full_payment=True)
        form_data = {'payment_method': 'online_full'}
        form = PaymentOptionForm(
            data=form_data,
            temp_booking=self.temp_booking_positive_total,
            hire_settings=settings
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['payment_method'], 'online_full')

    def test_clean_invalid_no_selection_when_choices_exist(self):
        """
        Test that the form is invalid when no selection is made but choices exist.
        """
        settings = create_hire_settings(enable_online_full_payment=True)
        form_data = {}                             
        form = PaymentOptionForm(
            data=form_data,
            temp_booking=self.temp_booking_positive_total,
            hire_settings=settings
        )
        self.assertFalse(form.is_valid())
        self.assertIn('payment_method', form.errors)
        self.assertIn('This field is required.', form.errors['payment_method'])

    def test_clean_valid_no_selection_when_no_choices_exist(self):
        """
        Test that the form is valid (and payment_method not required)
        when no payment options are enabled.
        """
        settings = create_hire_settings(
            enable_online_full_payment=False,
            enable_online_deposit_payment=False,
            enable_in_store_full_payment=False,
            deposit_enabled=False,
        )
        form_data = {}
        form = PaymentOptionForm(
            data=form_data,
            temp_booking=self.temp_booking_positive_total,
            hire_settings=settings
        )
        self.assertTrue(form.is_valid())
                                                                                                                                   
        self.assertEqual(form.cleaned_data.get('payment_method'), '') 
        self.assertFalse(form.fields['payment_method'].required)                         
