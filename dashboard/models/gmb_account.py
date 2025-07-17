from django.db import models


class GoogleMyBusinessAccount(models.Model):
    """
    Stores credentials and tokens for a single Google My Business account connection.
    This model follows a singleton pattern to ensure only one GMB account can be linked.
    """

    account_id = models.CharField(
        max_length=255, blank=True, null=True, help_text="Your GMB Account ID."
    )
    location_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="The ID of the specific business location.",
    )
    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    token_expiry = models.DateTimeField(blank=True, null=True)
    last_synced = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Google My Business Account"
        verbose_name_plural = "Google My Business Accounts"

    def __str__(self):
        if self.account_id and self.location_id:
            return f"Connected GMB Account: {self.account_id}"
        return "No GMB Account Connected"

    def save(self, *args, **kwargs):
        self.pk = 1
        super(GoogleMyBusinessAccount, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def is_configured(self):
        return bool(self.refresh_token)
