import binascii
import os
from typing import List

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.core.handlers.wsgi import WSGIRequest
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
    notes = models.TextField(blank=True)
    website_title = models.CharField(max_length=512, blank=True, null=True)
    website_description = models.TextField(blank=True, null=True)
    web_archive_snapshot_url = models.CharField(max_length=2048, blank=True)
    favicon_file = models.CharField(max_length=512, blank=True)
    unread = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    shared = models.BooleanField(default=False)
    date_added = models.DateTimeField()
    date_modified = models.DateTimeField()
    date_accessed = models.DateTimeField(blank=True, null=True)
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    tags = models.ManyToManyField(Tag)

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
    # Include website title and description as hidden field as they only provide info when editing bookmarks
    website_title = forms.CharField(max_length=512,
                                    required=False, widget=forms.HiddenInput())
    website_description = forms.CharField(required=False,
                                          widget=forms.HiddenInput())
    unread = forms.BooleanField(required=False)
    shared = forms.BooleanField(required=False)
    # Hidden field that determines whether to close window/tab after saving the bookmark
    auto_close = forms.CharField(required=False)

    class Meta:
        model = Bookmark
        fields = [
            'url',
            'tag_string',
            'title',
            'description',
            'notes',
            'website_title',
            'website_description',
            'unread',
            'shared',
            'auto_close',
        ]

    @property
    def has_notes(self):
        return self.instance and self.instance.notes


class BookmarkSearch:
    SORT_ADDED_ASC = 'added_asc'
    SORT_ADDED_DESC = 'added_desc'
    SORT_TITLE_ASC = 'title_asc'
    SORT_TITLE_DESC = 'title_desc'

    params = ['q', 'user', 'sort']
    defaults = {
        'q': '',
        'user': '',
        'sort': SORT_ADDED_DESC,
    }

    def __init__(self,
                 q: str = defaults['q'],
                 query: str = defaults['q'],  # alias for q
                 user: str = defaults['user'],
                 sort: str = defaults['sort']):
        self.q = q or query
        self.user = user
        self.sort = sort

    @property
    def query(self):
        return self.q

    def is_modified(self, param):
        value = self.__dict__[param]
        return value and value != BookmarkSearch.defaults[param]

    @property
    def modified_params(self):
        return [field for field in self.params if self.is_modified(field)]

    @property
    def query_params(self):
        return {param: self.__dict__[param] for param in self.modified_params}

    @staticmethod
    def from_request(request: WSGIRequest):
        initial_values = {}
        for param in BookmarkSearch.params:
            value = request.GET.get(param)
            if value:
                initial_values[param] = value

        return BookmarkSearch(**initial_values)


class BookmarkSearchForm(forms.Form):
    q = forms.CharField()
    user = forms.ChoiceField()
    sort = forms.CharField()

    def __init__(self, search: BookmarkSearch, editable_fields: List[str] = None, users: List[User] = None):
        super().__init__()
        editable_fields = editable_fields or []

        # set choices for user field if users are provided
        if users:
            user_choices = [(user.username, user.username) for user in users]
            user_choices.insert(0, ('', 'Everyone'))
            self.fields['user'].choices = user_choices

        for param in search.modified_params:
            # set initial values for modified params
            self.fields[param].initial = search.__dict__[param]

            # Mark non-editable modified fields as hidden. That way, templates
            # rendering a form can just loop over hidden_fields to ensure that
            # all necessary search options are kept when submitting the form.
            if param not in editable_fields:
                self.fields[param].widget = forms.HiddenInput()


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
    WEB_ARCHIVE_INTEGRATION_DISABLED = 'disabled'
    WEB_ARCHIVE_INTEGRATION_ENABLED = 'enabled'
    WEB_ARCHIVE_INTEGRATION_CHOICES = [
        (WEB_ARCHIVE_INTEGRATION_DISABLED, 'Disabled'),
        (WEB_ARCHIVE_INTEGRATION_ENABLED, 'Enabled'),
    ]
    TAG_SEARCH_STRICT = 'strict'
    TAG_SEARCH_LAX = 'lax'
    TAG_SEARCH_CHOICES = [
        (TAG_SEARCH_STRICT, 'Strict'),
        (TAG_SEARCH_LAX, 'Lax'),
    ]
    user = models.OneToOneField(get_user_model(), related_name='profile', on_delete=models.CASCADE)
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, blank=False, default=THEME_AUTO)
    bookmark_date_display = models.CharField(max_length=10, choices=BOOKMARK_DATE_DISPLAY_CHOICES, blank=False,
                                             default=BOOKMARK_DATE_DISPLAY_RELATIVE)
    bookmark_link_target = models.CharField(max_length=10, choices=BOOKMARK_LINK_TARGET_CHOICES, blank=False,
                                            default=BOOKMARK_LINK_TARGET_BLANK)
    web_archive_integration = models.CharField(max_length=10, choices=WEB_ARCHIVE_INTEGRATION_CHOICES, blank=False,
                                               default=WEB_ARCHIVE_INTEGRATION_DISABLED)
    tag_search = models.CharField(max_length=10, choices=TAG_SEARCH_CHOICES, blank=False,
                                  default=TAG_SEARCH_STRICT)
    enable_sharing = models.BooleanField(default=False, null=False)
    enable_public_sharing = models.BooleanField(default=False, null=False)
    enable_favicons = models.BooleanField(default=False, null=False)
    display_url = models.BooleanField(default=False, null=False)
    permanent_notes = models.BooleanField(default=False, null=False)


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['theme', 'bookmark_date_display', 'bookmark_link_target', 'web_archive_integration', 'tag_search',
                  'enable_sharing', 'enable_public_sharing', 'enable_favicons', 'display_url', 'permanent_notes']


@receiver(post_save, sender=get_user_model())
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=get_user_model())
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class Toast(models.Model):
    key = models.CharField(max_length=50)
    message = models.TextField()
    acknowledged = models.BooleanField(default=False)
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)


class FeedToken(models.Model):
    """
    Adapted from authtoken.models.Token
    """
    key = models.CharField(max_length=40, primary_key=True)
    user = models.OneToOneField(get_user_model(),
                                related_name='feed_token',
                                on_delete=models.CASCADE,
                                )
    created = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    @classmethod
    def generate_key(cls):
        return binascii.hexlify(os.urandom(20)).decode()

    def __str__(self):
        return self.key
