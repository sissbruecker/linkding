from django import forms
from django.contrib.auth import get_user_model
from django.db import models


class Tag(models.Model):
    name = models.CharField(max_length=64)
    date_added = models.DateTimeField()
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)


class Bookmark(models.Model):
    url = models.URLField()
    title = models.CharField(max_length=512)
    description = models.TextField()
    website_title = models.CharField(max_length=512, blank=True, null=True)
    website_description = models.TextField(blank=True, null=True)
    unread = models.BooleanField(default=True)
    date_added = models.DateTimeField()
    date_modified = models.DateTimeField()
    date_accessed = models.DateTimeField(blank=True, null=True)
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    tags = models.ManyToManyField(Tag)

    @property
    def resolved_title(self):
        return self.website_title if not self.title else self.title

    @property
    def resolved_description(self):
        return self.website_description if not self.description else self.description

    def __str__(self):
        return self.resolved_title + ' (' + self.url[:30] + '...)'


auto_fill_placeholder = 'Leave empty to fill from website metadata'


class BookmarkForm(forms.ModelForm):
    # Use URLField for URL
    url = forms.URLField()
    # Do not require title and description in form as we fill these automatically if they are empty
    title = forms.CharField(max_length=512,
                            required=False,
                            widget=forms.TextInput(attrs={'placeholder': auto_fill_placeholder}))
    description = forms.CharField(required=False,
                                  widget=forms.Textarea(attrs={'placeholder': auto_fill_placeholder}))

    class Meta:
        model = Bookmark
        fields = ['url', 'title', 'description']
