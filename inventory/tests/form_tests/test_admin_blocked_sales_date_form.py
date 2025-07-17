from django.test import TestCase
from inventory.forms import AdminBlockedSalesDateForm
from datetime import date, timedelta


class AdminBlockedSalesDateFormTest(TestCase):
    def test_valid_form_data(self):
        form = AdminBlockedSalesDateForm(
            data={
                "start_date": date.today(),
                "end_date": date.today() + timedelta(days=7),
                "description": "Test Blocked Period",
            }
        )
        self.assertTrue(form.is_valid())

    def test_end_date_before_start_date(self):
        form = AdminBlockedSalesDateForm(
            data={
                "start_date": date.today(),
                "end_date": date.today() - timedelta(days=1),
                "description": "Invalid Period",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("end_date", form.errors)
        self.assertEqual(
            form.errors["end_date"], ["End date cannot be before the start date."]
        )

    def test_empty_description_is_valid(self):
        form = AdminBlockedSalesDateForm(
            data={
                "start_date": date.today(),
                "end_date": date.today() + timedelta(days=1),
                "description": "",
            }
        )
        self.assertTrue(form.is_valid())

    def test_form_fields(self):
        form = AdminBlockedSalesDateForm()
        expected_fields = ["start_date", "end_date", "description"]
        self.assertEqual(list(form.fields.keys()), expected_fields)

    def test_form_widgets(self):
        form = AdminBlockedSalesDateForm()
        self.assertEqual(
            form.fields["start_date"].widget.attrs["class"],
            "form-control flatpickr-admin-date-input",
        )
        self.assertEqual(
            form.fields["end_date"].widget.attrs["class"],
            "form-control flatpickr-admin-date-input",
        )
        self.assertEqual(
            form.fields["description"].widget.attrs["class"], "form-control"
        )
        self.assertEqual(form.fields["description"].widget.attrs["rows"], 3)

    def test_form_labels(self):
        form = AdminBlockedSalesDateForm()
        self.assertEqual(form.fields["start_date"].label, "Start Date")
        self.assertEqual(form.fields["end_date"].label, "End Date")
        self.assertEqual(form.fields["description"].label, "Description (Optional)")

    def test_form_help_texts(self):
        form = AdminBlockedSalesDateForm()
        self.assertEqual(
            form.fields["start_date"].help_text, "The first date of the blocked period."
        )
        self.assertEqual(
            form.fields["end_date"].help_text,
            "The last date of the blocked period (inclusive).",
        )
        self.assertEqual(
            form.fields["description"].help_text,
            "A brief note about why these dates are blocked (e.g., 'Public Holiday', 'Staff Leave').",
        )
