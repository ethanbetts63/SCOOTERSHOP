from django.test import TestCase
from service.forms import AdminServiceTermsForm


class AdminServiceTermsFormTest(TestCase):
    def test_valid_form_data(self):
        form = AdminServiceTermsForm(
            data={"content": "These are some test service terms and conditions."}
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_empty_content(self):
        form = AdminServiceTermsForm(data={"content": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("content", form.errors)
        self.assertEqual(form.errors["content"], ["This field is required."])

    def test_form_widgets(self):
        form = AdminServiceTermsForm()
        self.assertEqual(form.fields["content"].widget.attrs["class"], "form-control")
        self.assertEqual(form.fields["content"].widget.attrs["rows"], 20)

    def test_form_labels(self):
        form = AdminServiceTermsForm()
        self.assertEqual(form.fields["content"].label, "Service Terms Content")

    def test_form_help_texts(self):
        form = AdminServiceTermsForm()
        self.assertEqual(
            form.fields["content"].help_text,
            "This text will be displayed to customers. Saving this form will create a new, active version and archive the previous one.",
        )
