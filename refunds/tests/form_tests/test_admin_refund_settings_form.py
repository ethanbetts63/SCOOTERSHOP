from django.test import TestCase
from decimal import Decimal
from django.core.exceptions import ValidationError
from payments.forms import RefundSettingsForm
from refunds.models import RefundSettings


class RefundSettingsFormTests(TestCase):

    def _get_valid_form_data(self):

        return {
            "full_payment_full_refund_days": 7,
            "full_payment_partial_refund_days": 3,
            "full_payment_partial_refund_percentage": Decimal("50.00"),
            "full_payment_no_refund_percentage": 1,
            "deposit_full_refund_days": 7,
            "deposit_partial_refund_days": 3,
            "deposit_partial_refund_percentage": Decimal("50.00"),
            "deposit_no_refund_days": 1,
        }

    def setUp(self):

        self.refund_settings, created = RefundSettings.objects.get_or_create(
            pk=1, defaults=self._get_valid_form_data()
        )

        if created:
            self.refund_settings.save()

    def test_form_valid_data(self):

        data = self._get_valid_form_data()
        data.update(
            {
                "full_payment_full_refund_days": 10,
                "full_payment_partial_refund_days": 5,
                "full_payment_partial_refund_percentage": Decimal("75.00"),
                "full_payment_no_refund_percentage": 2,
                "deposit_full_refund_days": 8,
                "deposit_partial_refund_days": 4,
                "deposit_partial_refund_percentage": Decimal("60.00"),
                "deposit_no_refund_days": 1,
                "": False,
                "sales_deposit_refund_grace_period_hours": 72,
                "sales_enable_deposit_refund": False,
            }
        )
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        updated_settings = form.save()
        self.assertEqual(
            updated_settings.full_payment_full_refund_days, 10
        )
        self.assertEqual(
            updated_settings.full_payment_partial_refund_percentage,
            Decimal("75.00"),
        )

        self.assertEqual(RefundSettings.objects.count(), 1)

    def test_form_invalid_percentage_fields(self):

        data = self._get_valid_form_data()
        data["full_payment_partial_refund_percentage"] = Decimal("101.00")
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "full_payment_partial_refund_percentage", form.errors
        )
        self.assertIn(
            "Ensure cancellation full payment partial refund percentage is between 0.00% and 100.00%.",
            form.errors["full_payment_partial_refund_percentage"],
        )

        data = self._get_valid_form_data()
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())

    def test_form_invalid_full_payment_days_thresholds(self):

        data = self._get_valid_form_data()
        data.update(
            {
                "full_payment_full_refund_days": 5,
                "full_payment_partial_refund_days": 10,
            }
        )
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())

        self.assertIn("full_payment_full_refund_days", form.errors)
        self.assertIn(
            "Full refund days must be greater than or equal to partial refund days.",
            form.errors["full_payment_full_refund_days"][0],
        )

        data = self._get_valid_form_data()
        data.update(
            {
                "full_payment_full_refund_days": 10,
                "full_payment_partial_refund_days": 5,
                "full_payment_no_refund_percentage": 10,
            }
        )
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("full_payment_partial_refund_days", form.errors)
        self.assertIn(
            "Partial refund days must be greater than or equal to minimal refund days.",
            form.errors["full_payment_partial_refund_days"][0],
        )

    def test_form_invalid_deposit_days_thresholds(self):

        data = self._get_valid_form_data()
        data.update(
            {
                "deposit_full_refund_days": 5,
                "deposit_partial_refund_days": 10,
            }
        )
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("deposit_full_refund_days", form.errors)
        self.assertIn(
            "Full deposit refund days must be greater than or equal to partial deposit refund days.",
            form.errors["deposit_full_refund_days"][0],
        )

        data = self._get_valid_form_data()
        data.update(
            {
                "deposit_full_refund_days": 10,
                "deposit_partial_refund_days": 5,
                "deposit_no_refund_days": 10,
            }
        )
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("deposit_partial_refund_days", form.errors)
        self.assertIn(
            "Partial deposit refund days must be greater than or equal to minimal deposit refund days.",
            form.errors["deposit_partial_refund_days"][0],
        )

    def test_form_no_new_instance_creation(self):

        data = self._get_valid_form_data()
        form = RefundSettingsForm(data=data)

        self.assertTrue(form.is_valid(), f"Form unexpectedly invalid: {form.errors}")

        with self.assertRaises(ValidationError) as cm:
            form.save()

        self.assertIn(
            "Only one instance of RefundSettings can be created. Please edit the existing one.",
            str(cm.exception),
        )

        self.assertEqual(RefundSettings.objects.count(), 1)

    def test_form_initial_data_for_existing_instance(self):

        initial_percentage = Decimal("45.00")
        initial_grace_hours = 36
        initial_enable_refund = False

        self.refund_settings.full_payment_partial_refund_percentage = (
            initial_percentage
        )
        self.refund_settings.sales_deposit_refund_grace_period_hours = (
            initial_grace_hours
        )
        self.refund_settings.sales_enable_deposit_refund = initial_enable_refund
        self.refund_settings.save()

        form = RefundSettingsForm(instance=self.refund_settings)
        self.assertEqual(
            form.initial["full_payment_partial_refund_percentage"],
            initial_percentage,
        )
        self.assertEqual(
            form.initial["sales_deposit_refund_grace_period_hours"], initial_grace_hours
        )
        self.assertEqual(
            form.initial["sales_enable_deposit_refund"], initial_enable_refund
        )

    def test_sales_refund_settings_validation(self):

        data = self._get_valid_form_data()
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertTrue(
            form.is_valid(),
            f"Form unexpectedly invalid for valid sales settings: {form.errors}",
        )

        data_invalid_hours = self._get_valid_form_data()
        data_invalid_hours["sales_deposit_refund_grace_period_hours"] = -10
        form_invalid_hours = RefundSettingsForm(
            instance=self.refund_settings, data=data_invalid_hours
        )
        self.assertFalse(form_invalid_hours.is_valid())
        self.assertIn(
            "sales_deposit_refund_grace_period_hours", form_invalid_hours.errors
        )

        self.assertIn(
            "Sales deposit refund grace period hours cannot be negative.",
            form_invalid_hours.errors["sales_deposit_refund_grace_period_hours"][0],
        )
