# from django.test import TestCase, Client
# from django.urls import reverse
# from ...test_helpers.model_factories import UserFactory, EnquiryFactory


# class EnquiryDetailViewTest(TestCase):

#     @classmethod
#     def setUpTestData(cls):
#         cls.staff_user = UserFactory(is_staff=True)
#         cls.regular_user = UserFactory()
#         cls.enquiry = EnquiryFactory()
#         cls.login_url = reverse("users:login")
#         cls.detail_url = reverse("core:enquiry_detail", kwargs={"pk": cls.enquiry.pk})

#     def setUp(self):
#         self.client = Client()

#     def test_anonymous_user_redirected(self):
#         response = self.client.get(self.detail_url)
#         self.assertRedirects(response, f"{self.login_url}?next={self.detail_url}")

#     def test_regular_user_redirected(self):
#         self.client.force_login(self.regular_user)
#         response = self.client.get(self.detail_url)
#         self.assertRedirects(response, f"{self.login_url}?next={self.detail_url}")

#     def test_staff_user_can_access_view(self):
#         self.client.force_login(self.staff_user)
#         response = self.client.get(self.detail_url)
#         self.assertEqual(response.status_code, 200)
#         self.assertTemplateUsed(response, "core/admin/enquiry_detail.html")
#         self.assertEqual(response.context["enquiry"], self.enquiry)
#         self.assertEqual(response.context["page_title"], "Enquiry Details")

#     def test_view_returns_404_for_non_existent_enquiry(self):
#         self.client.force_login(self.staff_user)
#         non_existent_url = reverse("core:enquiry_detail", kwargs={"pk": 999})
#         response = self.client.get(non_existent_url)
#         self.assertEqual(response.status_code, 404)
