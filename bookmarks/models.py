from typing import List

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from bookmarks.utils import unique
from bookmarks.validators import BookmarkURLValidator


class Tag(models.Model):
    name = models.CharField(max_length=64)
    date_added = models.DateTimeField()
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)

    def __str__(self):
        return self.name


def sanitize_tag_name(tag_name: str):
    # strip leading/trailing spaces
    # replace inner spaces with replacement char
    return tag_name.strip().replace(' ', '-')


def parse_tag_string(tag_string: str, delimiter: str = ','):
    if not tag_string:
        return []
    names = tag_string.strip().split(delimiter)
    # remove empty names, sanitize remaining names
    names = [sanitize_tag_name(name) for name in names if name]
    # remove duplicates
    names = unique(names, str.lower)
    names.sort(key=str.lower)

    return names


def build_tag_string(tag_names: List[str], delimiter: str = ','):
    return delimiter.join(tag_names)


class Bookmark(models.Model):
    url = models.CharField(max_length=2048, validators=[BookmarkURLValidator()])
    title = models.CharField(max_length=512, blank=True)
    description = models.TextField(blank=True)
    website_title = models.CharField(max_length=512, blank=True, null=True)
    website_description = models.TextField(blank=True, null=True)
    web_archive_snapshot_url = models.CharField(max_length=2048, blank=True)
    unread = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    date_added = models.DateTimeField()
    date_modified = models.DateTimeField()
    date_accessed = models.DateTimeField(blank=True, null=True)
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    tags = models.ManyToManyField(Tag)

    # Attributes might be calculated in query
    tag_count = 0  # Projection for number of associated tags
    tag_string = ''  # Projection for list of tag names, comma-separated
    tag_projection = False  # Tracks if the above projections were loaded

    @property
    def resolved_title(self):
        if self.title:
            return self.title
        elif self.website_title:
            return self.website_title
        else:
            return self.url

    @property
    def resolved_description(self):
        return self.website_description if not self.description else self.description

    @property
    def tag_names(self):
        # If tag projections were loaded then avoid querying all tags (=executing further selects)
        if self.tag_projection:
            return parse_tag_string(self.tag_string)
        else:
            return [tag.name for tag in self.tags.all()]

    def __str__(self):
        return self.resolved_title + ' (' + self.url[:30] + '...)'


class BookmarkForm(forms.ModelForm):
    # Use URLField for URL
    url = forms.CharField(validators=[BookmarkURLValidator()])
    tag_string = forms.CharField(required=False)
    # Do not require title and description in form as we fill these automatically if they are empty
    title = forms.CharField(max_length=512,
                            required=False)
    description = forms.CharField(required=False,
                                  widget=forms.Textarea())
    # Hidden field that determines whether to close window/tab after saving the bookmark
    auto_close = forms.CharField(required=False)

    class Meta:
        model = Bookmark
        fields = ['url', 'tag_string', 'title', 'description', 'auto_close']


class UserProfile(models.Model):
    THEME_AUTO = 'auto'
    THEME_LIGHT = 'light'
    THEME_DARK = 'dark'
    THEME_CHOICES = [
        (THEME_AUTO, 'Auto'),
        (THEME_LIGHT, 'Light'),
        (THEME_DARK, 'Dark'),
    ]
    BOOKMARK_DATE_DISPLAY_RELATIVE = 'relative'
    BOOKMARK_DATE_DISPLAY_ABSOLUTE = 'absolute'
    BOOKMARK_DATE_DISPLAY_HIDDEN = 'hidden'
    BOOKMARK_DATE_DISPLAY_CHOICES = [
        (BOOKMARK_DATE_DISPLAY_RELATIVE, 'Relative'),
        (BOOKMARK_DATE_DISPLAY_ABSOLUTE, 'Absolute'),
        (BOOKMARK_DATE_DISPLAY_HIDDEN, 'Hidden'),
    ]
    BOOKMARK_LINK_TARGET_BLANK = '_blank'
    BOOKMARK_LINK_TARGET_SELF = '_self'
    BOOKMARK_LINK_TARGET_CHOICES = [
        (BOOKMARK_LINK_TARGET_BLANK, 'New page'),
        (BOOKMARK_LINK_TARGET_SELF, 'Same page'),
    ]
    user = models.OneToOneField(get_user_model(), related_name='profile', on_delete=models.CASCADE)
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, blank=False, default=THEME_AUTO)
    bookmark_date_display = models.CharField(max_length=10, choices=BOOKMARK_DATE_DISPLAY_CHOICES, blank=False,
                                             default=BOOKMARK_DATE_DISPLAY_RELATIVE)
    bookmark_link_target = models.CharField(max_length=10, choices=BOOKMARK_LINK_TARGET_CHOICES, blank=False,
                                            default=BOOKMARK_LINK_TARGET_BLANK)


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['theme', 'bookmark_date_display', 'bookmark_link_target']


@receiver(post_save, sender=get_user_model())
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=get_user_model())
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
