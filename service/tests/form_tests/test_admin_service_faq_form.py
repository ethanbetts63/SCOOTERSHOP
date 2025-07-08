from django.test import TestCase
from service.forms import AdminServicefaqForm
from service.models import Servicefaq

class AdminServicefaqFormTest(TestCase):

    def test_valid_form_data(self):
        form = AdminServicefaqForm(data={
            'booking_step': Servicefaq.BOOKING_STEP_CHOICES[0][0],
            'question': 'Test Question',
            'answer': 'Test Answer',
            'display_order': 1,
            'is_active': True,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_fields(self):
        form = AdminServicefaqForm()
        expected_fields = ['booking_step', 'question', 'answer', 'display_order', 'is_active']
        self.assertEqual(list(form.fields.keys()), expected_fields)

    def test_form_widgets(self):
        form = AdminServicefaqForm()
        self.assertEqual(form.fields['booking_step'].widget.attrs['class'], 'form-control w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500')
        self.assertEqual(form.fields['question'].widget.attrs['class'], 'form-control w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500')
        self.assertEqual(form.fields['answer'].widget.attrs['class'], 'form-control w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500')
        self.assertEqual(form.fields['display_order'].widget.attrs['class'], 'form-control w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500')
        self.assertEqual(form.fields['is_active'].widget.attrs['class'], 'form-checkbox h-5 w-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500')

    def test_form_labels(self):
        form = AdminServicefaqForm()
        self.assertEqual(form.fields['booking_step'].label, 'Associated Service Step')
        self.assertEqual(form.fields['question'].label, 'Question')
        self.assertEqual(form.fields['answer'].label, 'Answer')
        self.assertEqual(form.fields['display_order'].label, 'Display Order')
        self.assertEqual(form.fields['is_active'].label, 'Is this faq active and visible?')

    def test_form_help_texts(self):
        form = AdminServicefaqForm()
        self.assertEqual(form.fields['display_order'].help_text, 'faqs with lower numbers will be shown first.')
        self.assertEqual(form.fields['is_active'].help_text, 'If unchecked, this faq will not be displayed anywhere on the site.')