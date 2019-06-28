from django.contrib.auth import get_user_model
from django.db import models


# Create your models here.
class Bookmark(models.Model):
    url = models.TextField()
    title = models.CharField(max_length=512)
    description = models.TextField()
    website_title = models.CharField(max_length=512)
    website_description = models.TextField()
    unread = models.BooleanField(default=True)
    date_added = models.DateTimeField()
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)

    @property
    def resolved_title(self):
        return self.website_title if not self.title else self.title

    @property
    def resolved_description(self):
        return self.website_description if not self.description else self.description

    def __str__(self):
        return self.title + ' (' + self.url[:30] + '...)'
