from django.db import models
from .page_content_base import PageContentBase # Import the base class

# Content for About page
class AboutPageContent(PageContentBase):
    intro_text = models.TextField(help_text="Introduction text at the top of the About page")
    sales_title = models.CharField(max_length=100, default="Sales")
    sales_content = models.TextField(help_text="Content for the Sales section")
    sales_image = models.FileField(upload_to='about/', help_text="Image for the Sales section", null=True, blank=True)

    service_title = models.CharField(max_length=100, default="Service")
    service_content = models.TextField(help_text="Content for the Service section")
    service_image = models.FileField(upload_to='about/', help_text="Image for the Service section", null=True, blank=True)

    parts_title = models.CharField(max_length=100, default="Parts & Accessories")
    parts_content = models.TextField(help_text="Content for the Parts & Accessories section")
    parts_image = models.FileField(upload_to='about/', help_text="Image for the Parts section", null=True, blank=True)

    cta_text = models.TextField(help_text="Call to action text at the bottom of the page")

    def __str__(self):
        return "About Page Content"

    class Meta:
        verbose_name = "About Page Content"
        verbose_name_plural = "About Page Content"

