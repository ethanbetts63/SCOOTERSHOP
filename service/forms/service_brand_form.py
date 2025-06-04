from django import forms
from service.models import ServiceBrand

class ServiceBrandForm(forms.ModelForm):
    class Meta:
        model = ServiceBrand
        fields = ['name', 'image', 'is_primary']
        help_texts = {
            'name': "The name of the service brand.",
            'image': f"Upload an image for this brand. Required for 'Primary' brands.",
            'is_primary': f"Check this box to mark the brand as primary (limit: 5). Requires an image."
        }

    def clean(self):
        cleaned_data = super().clean()
        is_primary = cleaned_data.get('is_primary')
        image = cleaned_data.get('image')

        # Server-side validation: Primary requires image
        if is_primary and not image:
            self.add_error('image', "Primary brands require an image.")

        return cleaned_data