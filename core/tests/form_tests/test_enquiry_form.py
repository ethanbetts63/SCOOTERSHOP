# from django.test import TestCase
# from core.forms.enquiry_form import EnquiryForm


# class EnquiryFormTest(TestCase):

#     def test_form_valid_data(self):
#         data = {
#             "name": "John Doe",
#             "email": "john.doe@example.com",
#             "phone_number": "1234567890",
#             "message": "This is a test enquiry.",
#         }
#         form = EnquiryForm(data=data)
#         self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

#     def test_form_invalid_data_missing_required_fields(self):
#         data = {
#             "name": "",
#             "email": "",
#             "message": "",
#         }
#         form = EnquiryForm(data=data)
#         self.assertFalse(form.is_valid())
#         self.assertIn("name", form.errors)
#         self.assertIn("email", form.errors)
#         self.assertIn("message", form.errors)
#         self.assertIn("This field is required.", form.errors["name"])
#         self.assertIn("This field is required.", form.errors["email"])
#         self.assertIn("This field is required.", form.errors["message"])

#     def test_form_invalid_data_invalid_email(self):
#         data = {
#             "name": "John Doe",
#             "email": "invalid-email",
#             "phone_number": "1234567890",
#             "message": "This is a test enquiry.",
#         }
#         form = EnquiryForm(data=data)
#         self.assertFalse(form.is_valid())
#         self.assertIn("email", form.errors)
#         self.assertIn("Enter a valid email address.", form.errors["email"])

#     def test_form_phone_number_optional(self):
#         data = {
#             "name": "Jane Doe",
#             "email": "jane.doe@example.com",
#             "message": "Another test enquiry.",
#         }
#         form = EnquiryForm(data=data)
#         self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
#         self.assertIsNone(form.cleaned_data["phone_number"])
