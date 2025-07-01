                                                              

from django.test import TestCase, Client
from django.urls import reverse

class UserConfirmationRefundRequestViewTests(TestCase):
    """
    Tests for the UserConfirmationRefundRequestView.
    This view displays a static confirmation page after a user successfully
    submits a refund request, informing them to check their email.
    """

    def setUp(self):
        """
        Set up test data and client for UserConfirmationRefundRequestView tests.
        """
        self.client = Client()
        self.confirmation_url = reverse('payments:user_confirmation_refund_request')

    def test_get_request_renders_correctly(self):
        """
        Test that a GET request to the UserConfirmationRefundRequestView renders the
        correct template and returns a 200 OK status.
        """
        response = self.client.get(self.confirmation_url)

                                                          
        self.assertEqual(response.status_code, 200)

                                                  
        self.assertTemplateUsed(response, 'payments/user_confirmation_refund_request.html')

    def test_context_data_is_correct(self):
        """
        Test that the context data passed to the template is correct.
        """
        response = self.client.get(self.confirmation_url)

                                                                           
        self.assertIn('page_title', response.context)
        self.assertEqual(response.context['page_title'], 'Refund Request Submitted')

        self.assertIn('message', response.context)
        self.assertEqual(
            response.context['message'],
            'Your refund request has been submitted successfully. A confirmation email has been sent to your inbox. Please click the link in the email to confirm your refund request.'
        )

        self.assertIn('additional_info', response.context)
        self.assertEqual(
            response.context['additional_info'],
            'If you do not receive an email within a few minutes, please check your spam folder.'
        )

    def test_content_contains_expected_text(self):
        """
        Test that the rendered page content contains the expected messages.
        """
        response = self.client.get(self.confirmation_url)

                                                               
        content = response.content.decode('utf-8')

                                                                         
        self.assertIn("Refund Request Submitted", content)
        self.assertIn("Your refund request has been submitted successfully.", content)
        self.assertIn("A confirmation email has been sent to your inbox.", content)
        self.assertIn("Please click the link in the email to confirm your refund request.", content)
        self.assertIn("If you do not receive an email within a few minutes, please check your spam folder.", content)

