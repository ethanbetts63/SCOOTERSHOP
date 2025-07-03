# from django.test import TestCase, Client
# from django.urls import reverse
# from django.contrib.messages import get_messages
# from core.models.enquiry import Enquiry
# from ...test_helpers.model_factories import UserFactory, EnquiryFactory


# class EnquiryDeleteViewTest(TestCase):

#     def setUp(self):
#         self.client = Client()
#         self.staff_user = UserFactory(is_staff=True)
#         self.regular_user = UserFactory()
#         self.enquiry = EnquiryFactory()

#         self.login_url = reverse("users:login")
#         self.management_url = reverse("core:enquiry_management")
#         self.delete_url = reverse("core:enquiry_delete", kwargs={"pk": self.enquiry.pk})

#     def test_anonymous_user_redirected(self):
#         response = self.client.post(self.delete_url)
#         self.assertRedirects(response, f"{self.login_url}?next={self.delete_url}")

#     def test_regular_user_redirected(self):
#         self.client.force_login(self.regular_user)
#         response = self.client.post(self.delete_url)
#         self.assertRedirects(response, f"{self.login_url}?next={self.delete_url}")

#     def test_get_request_redirects_to_management_view(self):
#         self.client.force_login(self.staff_user)
#         response = self.client.get(self.delete_url, follow=True)

#         self.assertRedirects(response, self.management_url)
#         messages = list(get_messages(response.wsgi_request))
#         self.assertEqual(len(messages), 1)
#         self.assertEqual(
#             str(messages[0]), "Please confirm deletion via the management page."
#         )

#     def test_post_request_deletes_enquiry(self):
#         self.client.force_login(self.staff_user)
#         initial_count = Enquiry.objects.count()

#         response = self.client.post(self.delete_url, follow=True)

#         self.assertEqual(Enquiry.objects.count(), initial_count - 1)
#         self.assertRedirects(response, self.management_url)

#         messages = list(get_messages(response.wsgi_request))
#         self.assertEqual(len(messages), 1)
#         self.assertIn("was deleted successfully", str(messages[0]))

#     def test_post_to_non_existent_enquiry_returns_404(self):
#         self.client.force_login(self.staff_user)
#         non_existent_url = reverse("core:enquiry_delete", kwargs={"pk": 999})
#         response = self.client.post(non_existent_url)
#         self.assertEqual(response.status_code, 404)
