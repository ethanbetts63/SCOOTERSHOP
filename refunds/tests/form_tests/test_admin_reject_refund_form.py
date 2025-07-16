from django.test import TestCase
from refunds.forms import AdminRejectRefundForm

class AdminRejectRefundFormTest(TestCase):

    def test_valid_form_data(self):
        form = AdminRejectRefundForm(data={
            'rejection_reason': 'Customer did not provide sufficient proof.',
            'send_rejection_email': True,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_empty_rejection_reason(self):
        form = AdminRejectRefundForm(data={
            'rejection_reason': '',
            'send_rejection_email': True,
        })
        # The form should be valid if rejection_reason is not a required field in the model
        self.assertTrue(form.is_valid())

    def test_form_fields(self):
        form = AdminRejectRefundForm()
        expected_fields = ['rejection_reason', 'send_rejection_email']
        self.assertEqual(list(form.fields.keys()), expected_fields)

    def test_form_widgets(self):
        form = AdminRejectRefundForm()
        self.assertEqual(form.fields['rejection_reason'].widget.attrs['rows'], 5)
        self.assertIn('form-control', form.fields['rejection_reason'].widget.attrs['class'])
        self.assertIn('form-check-input', form.fields['send_rejection_email'].widget.attrs['class'])

    def test_form_labels(self):
        form = AdminRejectRefundForm()
        self.assertEqual(form.fields['rejection_reason'].label, 'Reason for Rejection')
        self.assertEqual(form.fields['send_rejection_email'].label, 'Send automated rejection email to user')

    def test_form_help_texts(self):
        form = AdminRejectRefundForm()
        self.assertEqual(form.fields['rejection_reason'].help_text, 'Provide a clear and concise reason for rejecting this refund request.')
        self.assertEqual(form.fields['send_rejection_email'].help_text, 'If checked, an email containing the rejection reason will be sent to the user.')
