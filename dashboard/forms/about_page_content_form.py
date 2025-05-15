from django import forms
from ..models import AboutPageContent

class AboutPageContentForm(forms.ModelForm):
    class Meta:
        model = AboutPageContent
        fields = ['intro_text', 'sales_title', 'sales_content', 'sales_image',
                 'service_title', 'service_content', 'service_image',
                 'parts_title', 'parts_content', 'parts_image', 'cta_text']
        widgets = {
            'intro_text': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'sales_content': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'service_content': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'parts_content': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'cta_text': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'sales_title': forms.TextInput(attrs={'class': 'form-control'}),
            'service_title': forms.TextInput(attrs={'class': 'form-control'}),
            'parts_title': forms.TextInput(attrs={'class': 'form-control'}),
            # Use ClearableFileInput for images to allow removing existing files
            'sales_image': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'service_image': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'parts_image': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }