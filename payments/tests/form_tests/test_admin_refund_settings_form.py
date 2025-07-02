from django.test import TestCase
from decimal import Decimal
from django.core.exceptions import ValidationError
from payments.forms import RefundSettingsForm
from payments.models import RefundPolicySettings


class RefundSettingsFormTests(TestCase):

    def _get_valid_form_data(self):

        return {
            "cancellation_full_payment_full_refund_days": 7,
            "cancellation_full_payment_partial_refund_days": 3,
            "cancellation_full_payment_partial_refund_percentage": Decimal("50.00"),
            "cancellation_full_payment_minimal_refund_days": 1,
            "cancellation_full_payment_minimal_refund_percentage": Decimal("0.00"),
            "cancellation_deposit_full_refund_days": 7,
            "cancellation_deposit_partial_refund_days": 3,
            "cancellation_deposit_partial_refund_percentage": Decimal("50.00"),
            "cancellation_deposit_minimal_refund_days": 1,
            "cancellation_deposit_minimal_refund_percentage": Decimal("0.00"),
            "sales_enable_deposit_refund_grace_period": True,
            "sales_deposit_refund_grace_period_hours": 48,
            "sales_enable_deposit_refund": True,
            "refund_deducts_stripe_fee_policy": True,
            "stripe_fee_percentage_domestic": Decimal("0.0170"),
            "stripe_fee_fixed_domestic": Decimal("0.30"),
            "stripe_fee_percentage_international": Decimal("0.0350"),
            "stripe_fee_fixed_international": Decimal("0.30"),
        }

    def setUp(self):

        self.refund_settings, created = RefundPolicySettings.objects.get_or_create(
            pk=1, defaults=self._get_valid_form_data()
        )

        if created:
            self.refund_settings.save()

    def test_form_valid_data(self):

        data = self._get_valid_form_data()
        data.update(
            {
                "cancellation_full_payment_full_refund_days": 10,
                "cancellation_full_payment_partial_refund_days": 5,
                "cancellation_full_payment_partial_refund_percentage": Decimal("75.00"),
                "cancellation_full_payment_minimal_refund_days": 2,
                "cancellation_full_payment_minimal_refund_percentage": Decimal("10.00"),
                "cancellation_deposit_full_refund_days": 8,
                "cancellation_deposit_partial_refund_days": 4,
                "cancellation_deposit_partial_refund_percentage": Decimal("60.00"),
                "cancellation_deposit_minimal_refund_days": 1,
                "cancellation_deposit_minimal_refund_percentage": Decimal("5.00"),
                "refund_deducts_stripe_fee_policy": False,
                "stripe_fee_percentage_domestic": Decimal("0.0180"),
                "stripe_fee_fixed_domestic": Decimal("0.40"),
                "stripe_fee_percentage_international": Decimal("0.0360"),
                "stripe_fee_fixed_international": Decimal("0.40"),
                "sales_enable_deposit_refund_grace_period": False,
                "sales_deposit_refund_grace_period_hours": 72,
                "sales_enable_deposit_refund": False,
            }
        )
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        updated_settings = form.save()
        self.assertEqual(
            updated_settings.cancellation_full_payment_full_refund_days, 10
        )
        self.assertEqual(
            updated_settings.cancellation_full_payment_partial_refund_percentage,
            Decimal("75.00"),
        )
        self.assertFalse(updated_settings.refund_deducts_stripe_fee_policy)
        self.assertEqual(
            updated_settings.stripe_fee_percentage_domestic, Decimal("0.0180")
        )

        self.assertFalse(updated_settings.sales_enable_deposit_refund_grace_period)
        self.assertEqual(updated_settings.sales_deposit_refund_grace_period_hours, 72)
        self.assertFalse(updated_settings.sales_enable_deposit_refund)

        self.assertEqual(RefundPolicySettings.objects.count(), 1)

    def test_form_invalid_percentage_fields(self):

        data = self._get_valid_form_data()
        data["cancellation_full_payment_partial_refund_percentage"] = Decimal("101.00")
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "cancellation_full_payment_partial_refund_percentage", form.errors
        )
        self.assertIn(
            "Ensure cancellation full payment partial refund percentage is between 0.00% and 100.00%.",
            form.errors["cancellation_full_payment_partial_refund_percentage"],
        )

        data = self._get_valid_form_data()
        data["cancellation_deposit_minimal_refund_percentage"] = Decimal("-5.00")
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("cancellation_deposit_minimal_refund_percentage", form.errors)
        self.assertIn(
            "Ensure cancellation deposit minimal refund percentage is between 0.00% and 100.00%.",
            form.errors["cancellation_deposit_minimal_refund_percentage"],
        )

    def test_form_invalid_stripe_fee_percentage_fields(self):

        data = self._get_valid_form_data()
        data["stripe_fee_percentage_domestic"] = Decimal("0.1500")
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("stripe_fee_percentage_domestic", form.errors)
        self.assertIn(
            "Ensure domestic Stripe fee percentage is a sensible rate (e.g., 0.00 to 0.10 for 0-10%).",
            form.errors["stripe_fee_percentage_domestic"],
        )

        data = self._get_valid_form_data()
        data["stripe_fee_percentage_international"] = Decimal("-0.0100")
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("stripe_fee_percentage_international", form.errors)
        self.assertIn(
            "Ensure international Stripe fee percentage is a sensible rate (e.g., 0.00 to 0.10 for 0-10%).",
            form.errors["stripe_fee_percentage_international"],
        )

    def test_form_invalid_full_payment_days_thresholds(self):

        data = self._get_valid_form_data()
        data.update(
            {
                "cancellation_full_payment_full_refund_days": 5,
                "cancellation_full_payment_partial_refund_days": 10,
            }
        )
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())

        self.assertIn("cancellation_full_payment_full_refund_days", form.errors)
        self.assertIn(
            "Full refund days must be greater than or equal to partial refund days.",
            form.errors["cancellation_full_payment_full_refund_days"][0],
        )

        data = self._get_valid_form_data()
        data.update(
            {
                "cancellation_full_payment_full_refund_days": 10,
                "cancellation_full_payment_partial_refund_days": 5,
                "cancellation_full_payment_minimal_refund_days": 10,
            }
        )
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("cancellation_full_payment_partial_refund_days", form.errors)
        self.assertIn(
            "Partial refund days must be greater than or equal to minimal refund days.",
            form.errors["cancellation_full_payment_partial_refund_days"][0],
        )

    def test_form_invalid_deposit_days_thresholds(self):

        data = self._get_valid_form_data()
        data.update(
            {
                "cancellation_deposit_full_refund_days": 5,
                "cancellation_deposit_partial_refund_days": 10,
            }
        )
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("cancellation_deposit_full_refund_days", form.errors)
        self.assertIn(
            "Full deposit refund days must be greater than or equal to partial deposit refund days.",
            form.errors["cancellation_deposit_full_refund_days"][0],
        )

        data = self._get_valid_form_data()
        data.update(
            {
                "cancellation_deposit_full_refund_days": 10,
                "cancellation_deposit_partial_refund_days": 5,
                "cancellation_deposit_minimal_refund_days": 10,
            }
        )
        form = RefundSettingsForm(instance=self.refund_settings, data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("cancellation_deposit_partial_refund_days", form.errors)
        self.assertIn(
            "Partial deposit refund days must be greater than or equal to minimal deposit refund days.",
            form.errors["cancellation_deposit_partial_refund_days"][0],
        )

    def test_form_no_new_instance_creation(self):

        data = self._get_valid_form_data()
        form = RefundSettingsForm(data=data)

        self.assertTrue(form.is_valid(), f"Form unexpectedly invalid: {form.errors}")

        with self.assertRaises(ValidationError) as cm:
            form.save()

        self.assertIn(
            "Only one instance of RefundPolicySettings can be created. Please edit the existing one.",
            str(cm.exception),
        )

        self.assertEqual(RefundPolicySettings.objects.count(), 1)

    def test_form_initial_data_for_existing_instance(self):

        initial_percentage = Decimal("45.00")
        initial_grace_hours = 36
        initial_enable_refund = False

        self.refund_settings.cancellation_full_payment_partial_refund_percentage = (
            initial_percentage
        )
        self.refund_settings.sales_deposit_refund_grace_period_hours = (
            initial_grace_hours
        )
        self.refund_settings.sales_enable_deposit_refund = initial_enable_refund
        self.refund_settings.save()

        form = RefundSettingsForm(instance=self.refund_settings)
        self.assertEqual(
            form.initial["cancellation_full_payment_partial_refund_percentage"],
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
        data["sales_enable_deposit_refund_grace_period"] = True
        data["sales_deposit_refund_grace_period_hours"] = 24
        data["sales_enable_deposit_refund"] = True
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
