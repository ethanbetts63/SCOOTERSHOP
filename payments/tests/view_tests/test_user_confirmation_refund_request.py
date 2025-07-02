                                                              

from django.test import TestCase, Client
from django.urls import reverse

class UserConfirmationRefundRequestViewTests(TestCase):
    

    def setUp(self):
        
        self.client = Client()
        self.confirmation_url = reverse('payments:user_confirmation_refund_request')

    def test_get_request_renders_correctly(self):
        
        response = self.client.get(self.confirmation_url)

                                                          
        self.assertEqual(response.status_code, 200)

                                                  
        self.assertTemplateUsed(response, 'payments/user_confirmation_refund_request.html')

    def test_context_data_is_correct(self):
        
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
        
        response = self.client.get(self.confirmation_url)

                                                               
        content = response.content.decode('utf-8')

                                                                         
        self.assertIn("Refund Request Submitted", content)
        self.assertIn("Your refund request has been submitted successfully.", content)
        self.assertIn("A confirmation email has been sent to your inbox.", content)
        self.assertIn("Please click the link in the email to confirm your refund request.", content)
        self.assertIn("If you do not receive an email within a few minutes, please check your spam folder.", content)

