# hire/tests/form_tests/test_admin_hire_form.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date, time, timedelta
from decimal import Decimal

# Import the form to be tested
from hire.forms.Admin_Hire_Booking_form import AdminHireBookingForm

# Import model factories
from hire.tests.test_helpers.model_factories import(
    create_motorcycle,
    create_driver_profile,
    create_addon,
    create_package,
    create_hire_booking,
    create_booking_addon,
    create_hire_settings
)

# Import models for direct access if needed (e.g., for querysets)
from inventory.models import Motorcycle
from hire.models import AddOn, Package, DriverProfile, HireBooking
from hire.models.hire_booking import PAYMENT_STATUS_CHOICES, STATUS_CHOICES, PAYMENT_METHOD_CHOICES


class AdminHireBookingFormTest(TestCase):
    """
    Tests for the AdminHireBookingForm.
    Focuses on the clean method and form initialization.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up data for the entire test class.
        This runs once for all tests in this class.
        """
        # Ensure HireSettings exists for lead time validation
        cls.hire_settings = create_hire_settings(booking_lead_time_hours=1)

        # Create essential instances using factories
        cls.motorcycle = create_motorcycle(daily_hire_rate=Decimal('150.00'), hourly_hire_rate=Decimal('25.00'))
        cls.driver_profile = create_driver_profile()
        cls.addon1 = create_addon(name="GPS", cost=Decimal('15.00'), min_quantity=1, max_quantity=2)
        cls.addon2 = create_addon(name="Extra Helmet", cost=Decimal('10.00'), min_quantity=1, max_quantity=1)
        # Ensure this add-on is initially unavailable to test the form's __init__ change
        cls.unavailable_addon = create_addon(name="Unavailable Item", is_available=False) 
        cls.package = create_package(name="Premium Pack", package_price=Decimal('75.00'), add_ons=[cls.addon1])
        cls.unavailable_package = create_package(name="Out of Stock Pack", is_available=False)

    def _get_valid_form_data(self, **kwargs):
        """
        Helper to get a dictionary of valid form data.
        Allows overriding specific fields for testing.
        """
        data = {
            'pick_up_date': date.today() + timedelta(days=2),
            'pick_up_time': time(10, 0),
            'return_date': date.today() + timedelta(days=3),
            'return_time': time(10, 0),
            'motorcycle': self.motorcycle.id,
            'booked_daily_rate': Decimal('150.00'),
            'booked_hourly_rate': Decimal('25.00'),
            'package': self.package.id,
            'driver_profile': self.driver_profile.id,
            'currency': 'AUD',
            'total_price': Decimal('300.00'),
            'payment_method': 'card',
            'payment_status': 'unpaid',
            'status': 'pending',
            'internal_notes': 'Test booking notes.',
            # Add-on fields (default to not selected)
            f'addon_{self.addon1.id}_selected': False,
            f'addon_{self.addon1.id}_quantity': 1,
            f'addon_{self.addon2.id}_selected': False,
            f'addon_{self.addon2.id}_quantity': 1,
            f'addon_{self.unavailable_addon.id}_selected': False, # Include unavailable addon in default data
            f'addon_{self.unavailable_addon.id}_quantity': 1,
        }
        data.update(kwargs)
        return data

    def test_form_initialization_with_instance(self):
        """
        Test that the form correctly initializes with an existing HireBooking instance.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            pickup_date=date.today() + timedelta(days=5),
            pickup_time=time(9, 0),
            return_date=date.today() + timedelta(days=7),
            return_time=time(17, 0),
            package=self.package,
            total_price=Decimal('500.00'),
            payment_status='paid',
            status='confirmed'
        )
        create_booking_addon(booking=booking, addon=self.addon1, quantity=2)
        create_booking_addon(booking=booking, addon=self.addon2, quantity=1)

        form = AdminHireBookingForm(instance=booking)

        # Assert initial values are correctly set by checking form.fields[...].initial
        self.assertEqual(form.fields['pick_up_date'].initial, booking.pickup_date)
        self.assertEqual(form.fields['pick_up_time'].initial, booking.pickup_time)
        self.assertEqual(form.fields['motorcycle'].initial, booking.motorcycle) # Model instance comparison
        self.assertEqual(form.fields['package'].initial, booking.package) # Model instance comparison
        self.assertEqual(form.fields['total_price'].initial, booking.total_price)
        self.assertEqual(form.fields['payment_status'].initial, booking.payment_status)
        self.assertEqual(form.fields['status'].initial, booking.status)

        # Assert add-on initial values are correctly set
        self.assertTrue(form.fields[f'addon_{self.addon1.id}_selected'].initial)
        self.assertEqual(form.fields[f'addon_{self.addon1.id}_quantity'].initial, 2)
        self.assertTrue(form.fields[f'addon_{self.addon2.id}_selected'].initial)
        self.assertEqual(form.fields[f'addon_{self.addon2.id}_quantity'].initial, 1)

    def test_valid_form_data(self):
        """
        Test that a form with valid data passes validation.
        """
        form = AdminHireBookingForm(data=self._get_valid_form_data())
        self.assertTrue(form.is_valid(), form.errors.as_json())
        # Check that selected_addons_data and selected_package_instance are populated
        self.assertIn('selected_addons_data', form.cleaned_data)
        self.assertIn('selected_package_instance', form.cleaned_data)
        self.assertEqual(form.cleaned_data['selected_package_instance'], self.package)

    def test_pickup_after_return_date_time_validation(self):
        """
        Test that the form raises a ValidationError if return_datetime <= pickup_datetime.
        """
        data = self._get_valid_form_data(
            pick_up_date=date.today() + timedelta(days=2),
            pick_up_time=time(10, 0),
            return_date=date.today() + timedelta(days=2), # Same day
            return_time=time(9, 0) # Before pickup time
        )
        form = AdminHireBookingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('return_date', form.errors)
        self.assertIn('return_time', form.errors)
        self.assertEqual(
            form.errors['return_date'][0],
            "Return date and time must be after pickup date and time."
        )

        data = self._get_valid_form_data(
            pick_up_date=date.today() + timedelta(days=2),
            pick_up_time=time(10, 0),
            return_date=date.today() + timedelta(days=2), # Same day
            return_time=time(10, 0) # Same time
        )
        form = AdminHireBookingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('return_date', form.errors)

    def test_total_price_negative(self):
        """
        Test that total_price cannot be negative.
        """
        data = self._get_valid_form_data(total_price=Decimal('-10.00'))
        form = AdminHireBookingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('total_price', form.errors)
        self.assertEqual(form.errors['total_price'][0], "Total price cannot be negative.")

    def test_total_price_zero_with_paid_status(self):
        """
        Test that total_price must be > 0 if payment_status is 'Fully Paid'.
        """
        data = self._get_valid_form_data(total_price=Decimal('0.00'), payment_status='paid')
        form = AdminHireBookingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('total_price', form.errors)
        self.assertEqual(form.errors['total_price'][0], "Total price must be greater than 0 if payment status is 'Fully Paid'.")

        # Test with total_price=None when payment_status is 'paid'
        data = self._get_valid_form_data(total_price=None, payment_status='paid')
        form = AdminHireBookingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('total_price', form.errors)
        self.assertEqual(form.errors['total_price'][0], "Total price must be greater than 0 if payment status is 'Fully Paid'.")

    def test_addon_quantity_validation(self):
        """
        Test that add-on quantities are validated against min/max.
        """
        # Test quantity below min
        data = self._get_valid_form_data(
            **{f'addon_{self.addon1.id}_selected': True, f'addon_{self.addon1.id}_quantity': 0}
        )
        form = AdminHireBookingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn(f'addon_{self.addon1.id}_quantity', form.errors)
        self.assertIn(f"Quantity for {self.addon1.name} must be between {self.addon1.min_quantity}-{self.addon1.max_quantity}.",
                      form.errors[f'addon_{self.addon1.id}_quantity'])

        # Test quantity above max
        data = self._get_valid_form_data(
            **{f'addon_{self.addon1.id}_selected': True, f'addon_{self.addon1.id}_quantity': 3}
        )
        form = AdminHireBookingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn(f'addon_{self.addon1.id}_quantity', form.errors)
        self.assertIn(f"Quantity for {self.addon1.name} must be between {self.addon1.min_quantity}-{self.addon1.max_quantity}.",
                      form.errors[f'addon_{self.addon1.id}_quantity'])

        # Test valid quantity
        data = self._get_valid_form_data(
            **{f'addon_{self.addon1.id}_selected': True, f'addon_{self.addon1.id}_quantity': 2}
        )
        form = AdminHireBookingForm(data=data)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        # Check that selected_addons_data contains the correct add-on and quantity
        selected_addon = next((item for item in form.cleaned_data['selected_addons_data'] if item['addon'] == self.addon1), None)
        self.assertIsNotNone(selected_addon)
        self.assertEqual(selected_addon['quantity'], 2)
        self.assertEqual(selected_addon['price'], self.addon1.cost)


    def test_booked_rates_non_negative(self):
        """
        Test that booked_daily_rate and booked_hourly_rate cannot be negative.
        """
        data = self._get_valid_form_data(booked_daily_rate=Decimal('-5.00'))
        form = AdminHireBookingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('booked_daily_rate', form.errors)
        self.assertEqual(form.errors['booked_daily_rate'][0], "Booked daily rate cannot be negative.")

        data = self._get_valid_form_data(booked_hourly_rate=Decimal('-2.00'))
        form = AdminHireBookingForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('booked_hourly_rate', form.errors)
        self.assertEqual(form.errors['booked_hourly_rate'][0], "Booked hourly rate cannot be negative.")

    def test_international_booking_and_australian_resident_consistency(self):
        """
        Test that an international booking cannot be made for an Australian resident.
        NOTE: This validation is handled in the HireBooking model's clean method, not the form's.
        """
        pass # Skipping this test as it's not handled by the form's clean method.

    def test_form_initialization_with_no_package_selected(self):
        """
        Test that the form initializes correctly when no package is selected in the instance.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            pickup_date=date.today() + timedelta(days=5),
            pickup_time=time(9, 0),
            return_date=date.today() + timedelta(days=7),
            return_time=time(17, 0),
            package=None, # No package
            total_price=Decimal('500.00'),
            payment_status='paid',
            status='confirmed'
        )
        form = AdminHireBookingForm(instance=booking)
        # Check initial value on the field itself
        self.assertIsNone(form.fields['package'].initial)

    def test_form_initialization_with_no_addons_selected(self):
        """
        Test that the form initializes correctly when no add-ons are selected in the instance.
        """
        booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            pickup_date=date.today() + timedelta(days=5),
            pickup_time=time(9, 0),
            return_date=date.today() + timedelta(days=7),
            return_time=time(17, 0),
            total_price=Decimal('500.00'),
            payment_status='paid',
            status='confirmed'
        )
        form = AdminHireBookingForm(instance=booking)
        # Check initial value on the field itself
        self.assertFalse(form.fields[f'addon_{self.addon1.id}_selected'].initial)
        self.assertEqual(form.fields[f'addon_{self.addon1.id}_quantity'].initial, 1) # Default quantity

    def test_dynamic_addon_fields_creation(self):
        """
        Test that add-on fields are dynamically created during form initialization.
        This now includes unavailable add-ons for admin purposes.
        """
        form = AdminHireBookingForm()
        self.assertIn(f'addon_{self.addon1.id}_selected', form.fields)
        self.assertIn(f'addon_{self.addon1.id}_quantity', form.fields)
        self.assertIn(f'addon_{self.addon2.id}_selected', form.fields)
        self.assertIn(f'addon_{self.addon2.id}_quantity', form.fields)
        # Ensure unavailable add-ons also get fields (as they might have been selected previously)
        self.assertIn(f'addon_{self.unavailable_addon.id}_selected', form.fields)
        self.assertIn(f'addon_{self.unavailable_addon.id}_quantity', form.fields)

    def test_get_addon_fields_helper(self):
        """
        Test the get_addon_fields helper method for template rendering.
        """
        form = AdminHireBookingForm(data=self._get_valid_form_data())
        form.is_valid() # Clean the data to ensure display_addons is processed

        addon_fields = list(form.get_addon_fields())
        self.assertEqual(len(addon_fields), len(form.display_addons))

        for field_info in addon_fields:
            self.assertIn('addon', field_info)
            self.assertIn('selected_field', field_info)
            self.assertIn('quantity_field', field_info)
            self.assertIsInstance(field_info['addon'], AddOn)
            self.assertIsNotNone(field_info['selected_field'])
            self.assertIsNotNone(field_info['quantity_field'])

    def test_motorcycle_queryset_and_label(self):
        """
        Test that motorcycle queryset is filtered and label_from_instance works.
        """
        # Create an unavailable motorcycle
        unavailable_motorcycle = create_motorcycle(title="Broken Bike", is_available=False)
        # Create a motorcycle not for hire
        non_hire_motorcycle = create_motorcycle(title="For Sale Bike")
        non_hire_motorcycle.conditions.clear() # Remove 'hire' condition

        form = AdminHireBookingForm()

        # Check queryset filters for available and 'hire' condition
        queryset_ids = set(form.fields['motorcycle'].queryset.values_list('id', flat=True))
        self.assertIn(self.motorcycle.id, queryset_ids)
        self.assertNotIn(unavailable_motorcycle.id, queryset_ids)
        self.assertNotIn(non_hire_motorcycle.id, queryset_ids)

        # Check label_from_instance
        label = form.fields['motorcycle'].label_from_instance(self.motorcycle)
        self.assertEqual(label, f"ID: {self.motorcycle.id} - {self.motorcycle.brand} {self.motorcycle.model} ({self.motorcycle.year})")

    def test_package_queryset_and_label(self):
        """
        Test that package queryset is filtered and label_from_instance works.
        """
        form = AdminHireBookingForm()

        # Check queryset filters for available packages
        queryset_ids = set(form.fields['package'].queryset.values_list('id', flat=True))
        self.assertIn(self.package.id, queryset_ids)
        self.assertNotIn(self.unavailable_package.id, queryset_ids)

        # Check label_from_instance
        label = form.fields['package'].label_from_instance(self.package)
        self.assertEqual(label, f"{self.package.name} ({self.package.package_price:.2f})")

