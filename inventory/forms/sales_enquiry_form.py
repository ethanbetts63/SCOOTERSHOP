from django import forms
from core.models.enquiry import Enquiry


class SalesEnquiryForm(forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = ["name", "email", "phone_number", "message", "motorcycle"]
