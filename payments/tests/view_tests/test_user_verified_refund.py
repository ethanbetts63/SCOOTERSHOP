from django.test import TestCase, Client
from django.urls import reverse


class UserVerifiedRefundViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()

    def test_get_request_renders_correct_template_and_context(self):
        url = reverse("payments:user_verified_refund")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, "payments/user_verified_refund.html")

        self.assertIn("page_title", response.context)
        self.assertEqual(response.context["page_title"], "Refund Request Verified")

        self.assertIn("message", response.context)
        self.assertEqual(
            response.context["message"],
            "Your refund request has been successfully verified!",
        )

        self.assertIn("additional_info", response.context)
        self.assertIn(
            "reviewed by our administration team", response.context["additional_info"]
        )
        self.assertIn(
            "another email once your request has been processed",
            response.context["additional_info"],
        )

    def test_get_request_renders_content_correctly(self):
        url = reverse("payments:user_verified_refund")
        response = self.client.get(url)

        content = response.content.decode("utf-8")

        self.assertIn("Refund Request Verified", content)
        self.assertIn("Your refund request has been successfully verified!", content)
        self.assertIn(
            "It will now be reviewed by our administration team as soon as possible.",
            content,
        )
        self.assertIn(
            "You will receive another email once your request has been processed.",
            content,
        )
