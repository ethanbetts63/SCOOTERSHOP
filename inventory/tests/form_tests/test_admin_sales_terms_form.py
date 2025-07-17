from django.test import TestCase
from inventory.forms import AdminSalesTermsForm


class AdminSalesTermsFormTest(TestCase):
    def test_valid_form_data(self):
        form = AdminSalesTermsForm(
            data={"content": "These are some test terms and conditions."}
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_empty_content(self):
        form = AdminSalesTermsForm(data={"content": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("content", form.errors)
        self.assertEqual(form.errors["content"], ["This field is required."])

    def test_form_widgets(self):
        form = AdminSalesTermsForm()
        self.assertEqual(form.fields["content"].widget.attrs["class"], "form-control")
        self.assertEqual(form.fields["content"].widget.attrs["rows"], 20)

    def test_form_labels(self):
        form = AdminSalesTermsForm()
        self.assertEqual(form.fields["content"].label, "Terms and Conditions Content")

    def test_form_help_texts(self):
        form = AdminSalesTermsForm()
        self.assertEqual(
            form.fields["content"].help_text,
            "This text will be displayed to customers during the booking process. Saving this form will create a new, active version and archive the previous one.",
        )
