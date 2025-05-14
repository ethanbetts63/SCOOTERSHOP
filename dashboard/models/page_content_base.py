from django.db import models

# Base model for page content
class PageContentBase(models.Model):
    """Base model for page content"""
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True 
