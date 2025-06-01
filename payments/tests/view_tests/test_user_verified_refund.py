# payments/tests/test_user_verified_refund_view.py

from django.test import TestCase, Client
from django.urls import reverse

class UserVerifiedRefundViewTests(TestCase):
    """
    Tests for the UserVerifiedRefundView.
    This view displays a static confirmation page after a refund request
    has been successfully verified.
    """

    def setUp(self):
        """
        Set up test data and client for UserVerifiedRefundView tests.
        """
        self.client = Client()
        self.verified_refund_url = reverse('payments:user_verified_refund')

    def test_get_request_renders_correctly(self):
        """
        Test that a GET request to the UserVerifiedRefundView renders the
        correct template and returns a 200 OK status.
        """
        response = self.client.get(self.verified_refund_url)

        # Assert that the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # Assert that the correct template is used
        self.assertTemplateUsed(response, 'payments/user_verified_refund.html')

    def test_context_data_is_correct(self):
        """
        Test that the context data passed to the template is correct.
        """
        response = self.client.get(self.verified_refund_url)

        # Check if the context variables exist and have the expected values
        self.assertIn('page_title', response.context)
        self.assertEqual(response.context['page_title'], 'Refund Request Verified')

        self.assertIn('message', response.context)
        self.assertEqual(response.context['message'], 'Your refund request has been successfully verified!')

        self.assertIn('additional_info', response.context)
        self.assertEqual(
            response.context['additional_info'],
            'It will now be reviewed by our administration team as soon as possible. You will receive another email once your request has been processed.'
        )

    def test_content_contains_expected_text(self):
        """
        Test that the rendered page content contains the expected messages.
        """
        response = self.client.get(self.verified_refund_url)

        # Decode the response content to a string for assertion
        content = response.content.decode('utf-8')

        # Assert that key pieces of text are present in the rendered HTML
        self.assertIn("Refund Request Verified", content)
        self.assertIn("Your refund request has been successfully verified!", content)
        self.assertIn("It will now be reviewed by our administration team as soon as possible.", content)
        self.assertIn("You will receive another email once your request has been processed.", content)

