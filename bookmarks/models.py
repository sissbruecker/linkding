import binascii
import hashlib
import logging
import os
from typing import List

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.http import QueryDict

from bookmarks.utils import unique
from bookmarks.validators import BookmarkURLValidator

logger = logging.getLogger(__name__)


class Tag(models.Model):
    name = models.CharField(max_length=64)
    date_added = models.DateTimeField()
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)

    def __str__(self):
        return self.name


def sanitize_tag_name(tag_name: str):
    # strip leading/trailing spaces
    # replace inner spaces with replacement char
    return tag_name.strip().replace(" ", "-")


def parse_tag_string(tag_string: str, delimiter: str = ","):
    if not tag_string:
        return []
    names = tag_string.strip().split(delimiter)
    # remove empty names, sanitize remaining names
    names = [sanitize_tag_name(name) for name in names if name]
    # remove duplicates
    names = unique(names, str.lower)
    names.sort(key=str.lower)

    return names


def build_tag_string(tag_names: List[str], delimiter: str = ","):
    return delimiter.join(tag_names)


class Bookmark(models.Model):
    url = models.CharField(max_length=2048, validators=[BookmarkURLValidator()])
    title = models.CharField(max_length=512, blank=True)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    # Obsolete field, kept to not remove column when generating migrations
    website_title = models.CharField(max_length=512, blank=True, null=True)
    # Obsolete field, kept to not remove column when generating migrations
    website_description = models.TextField(blank=True, null=True)
    web_archive_snapshot_url = models.CharField(max_length=2048, blank=True)
    favicon_file = models.CharField(max_length=512, blank=True)
    preview_image_file = models.CharField(max_length=512, blank=True)
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
        else:
            return self.url

    @property
    def resolved_description(self):
        return self.description

    @property
    def tag_names(self):
        names = [tag.name for tag in self.tags.all()]
        return sorted(names)

    def __str__(self):
        return self.resolved_title + " (" + self.url[:30] + "...)"


class BookmarkAsset(models.Model):
    TYPE_SNAPSHOT = "snapshot"
    TYPE_UPLOAD = "upload"

    CONTENT_TYPE_HTML = "text/html"

    STATUS_PENDING = "pending"
    STATUS_COMPLETE = "complete"
    STATUS_FAILURE = "failure"

    bookmark = models.ForeignKey(Bookmark, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True, null=False)
    file = models.CharField(max_length=2048, blank=True, null=False)
    file_size = models.IntegerField(null=True)
    asset_type = models.CharField(max_length=64, blank=False, null=False)
    content_type = models.CharField(max_length=128, blank=False, null=False)
    display_name = models.CharField(max_length=2048, blank=True, null=False)
    status = models.CharField(max_length=64, blank=False, null=False)
    gzip = models.BooleanField(default=False, null=False)

    def save(self, *args, **kwargs):
        if self.file:
            try:
                file_path = os.path.join(settings.LD_ASSET_FOLDER, self.file)
                if os.path.isfile(file_path):
                    self.file_size = os.path.getsize(file_path)
            except Exception:
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name or f"Bookmark Asset #{self.pk}"


@receiver(post_delete, sender=BookmarkAsset)
def bookmark_asset_deleted(sender, instance, **kwargs):
    if instance.file:
        filepath = os.path.join(settings.LD_ASSET_FOLDER, instance.file)
        if os.path.isfile(filepath):
            try:
                os.remove(filepath)
            except Exception as error:
                logger.error(f"Failed to delete asset file: {filepath}", exc_info=error)


class BookmarkForm(forms.ModelForm):
    # Use URLField for URL
    url = forms.CharField(validators=[BookmarkURLValidator()])
    tag_string = forms.CharField(required=False)
    # Do not require title and description as they may be empty
    title = forms.CharField(max_length=512, required=False)
    description = forms.CharField(required=False, widget=forms.Textarea())
    unread = forms.BooleanField(required=False)
    shared = forms.BooleanField(required=False)
    # Hidden field that determines whether to close window/tab after saving the bookmark
    auto_close = forms.CharField(required=False)

    class Meta:
        model = Bookmark
        fields = [
            "url",
            "tag_string",
            "title",
            "description",
            "notes",
            "unread",
            "shared",
            "auto_close",
        ]

    @property
    def has_notes(self):
        return self.initial.get("notes", None) or (
            self.instance and self.instance.notes
        )

    def clean_url(self):
        # When creating a bookmark, the service logic prevents duplicate URLs by
        # updating the existing bookmark instead, which is also communicated in
        # the form's UI. When editing a bookmark, there is no assumption that
        # it would update a different bookmark if the URL is a duplicate, so
        # raise a validation error in that case.
        url = self.cleaned_data["url"]
        if self.instance.pk:
            is_duplicate = (
                Bookmark.objects.filter(owner=self.instance.owner, url=url)
                .exclude(pk=self.instance.pk)
                .exists()
            )
            if is_duplicate:
                raise forms.ValidationError("A bookmark with this URL already exists.")

        return url


class BookmarkSearch:
    SORT_ADDED_ASC = "added_asc"
    SORT_ADDED_DESC = "added_desc"
    SORT_TITLE_ASC = "title_asc"
    SORT_TITLE_DESC = "title_desc"

    FILTER_SHARED_OFF = "off"
    FILTER_SHARED_SHARED = "yes"
    FILTER_SHARED_UNSHARED = "no"

    FILTER_UNREAD_OFF = "off"
    FILTER_UNREAD_YES = "yes"
    FILTER_UNREAD_NO = "no"

    params = ["q", "user", "sort", "shared", "unread"]
    preferences = ["sort", "shared", "unread"]
    defaults = {
        "q": "",
        "user": "",
        "sort": SORT_ADDED_DESC,
        "shared": FILTER_SHARED_OFF,
        "unread": FILTER_UNREAD_OFF,
    }

    def __init__(
        self,
        q: str = None,
        user: str = None,
        sort: str = None,
        shared: str = None,
        unread: str = None,
        preferences: dict = None,
    ):
        if not preferences:
            preferences = {}
        self.defaults = {**BookmarkSearch.defaults, **preferences}

        self.q = q or self.defaults["q"]
        self.user = user or self.defaults["user"]
        self.sort = sort or self.defaults["sort"]
        self.shared = shared or self.defaults["shared"]
        self.unread = unread or self.defaults["unread"]

    def is_modified(self, param):
        value = self.__dict__[param]
        return value != self.defaults[param]

    @property
    def modified_params(self):
        return [field for field in self.params if self.is_modified(field)]

    @property
    def modified_preferences(self):
        return [
            preference
            for preference in self.preferences
            if self.is_modified(preference)
        ]

    @property
    def has_modifications(self):
        return len(self.modified_params) > 0

    @property
    def has_modified_preferences(self):
        return len(self.modified_preferences) > 0

    @property
    def query_params(self):
        return {param: self.__dict__[param] for param in self.modified_params}

    @property
    def preferences_dict(self):
        return {
            preference: self.__dict__[preference] for preference in self.preferences
        }

    @staticmethod
    def from_request(query_dict: QueryDict, preferences: dict = None):
        initial_values = {}
        for param in BookmarkSearch.params:
            value = query_dict.get(param)
            if value:
                initial_values[param] = value

        return BookmarkSearch(**initial_values, preferences=preferences)


class BookmarkSearchForm(forms.Form):
    SORT_CHOICES = [
        (BookmarkSearch.SORT_ADDED_ASC, "Added ↑"),
        (BookmarkSearch.SORT_ADDED_DESC, "Added ↓"),
        (BookmarkSearch.SORT_TITLE_ASC, "Title ↑"),
        (BookmarkSearch.SORT_TITLE_DESC, "Title ↓"),
    ]
    FILTER_SHARED_CHOICES = [
        (BookmarkSearch.FILTER_SHARED_OFF, "Off"),
        (BookmarkSearch.FILTER_SHARED_SHARED, "Shared"),
        (BookmarkSearch.FILTER_SHARED_UNSHARED, "Unshared"),
    ]
    FILTER_UNREAD_CHOICES = [
        (BookmarkSearch.FILTER_UNREAD_OFF, "Off"),
        (BookmarkSearch.FILTER_UNREAD_YES, "Unread"),
        (BookmarkSearch.FILTER_UNREAD_NO, "Read"),
    ]

    q = forms.CharField()
    user = forms.ChoiceField(required=False)
    sort = forms.ChoiceField(choices=SORT_CHOICES)
    shared = forms.ChoiceField(choices=FILTER_SHARED_CHOICES, widget=forms.RadioSelect)
    unread = forms.ChoiceField(choices=FILTER_UNREAD_CHOICES, widget=forms.RadioSelect)

    def __init__(
        self,
        search: BookmarkSearch,
        editable_fields: List[str] = None,
        users: List[User] = None,
    ):
        super().__init__()
        editable_fields = editable_fields or []
        self.editable_fields = editable_fields

        # set choices for user field if users are provided
        if users:
            user_choices = [(user.username, user.username) for user in users]
            user_choices.insert(0, ("", "Everyone"))
            self.fields["user"].choices = user_choices

        for param in search.params:
            # set initial values for modified params
            self.fields[param].initial = search.__dict__[param]

            # Mark non-editable modified fields as hidden. That way, templates
            # rendering a form can just loop over hidden_fields to ensure that
            # all necessary search options are kept when submitting the form.
            if search.is_modified(param) and param not in editable_fields:
                self.fields[param].widget = forms.HiddenInput()


class UserProfile(models.Model):
    THEME_AUTO = "auto"
    THEME_LIGHT = "light"
    THEME_DARK = "dark"
    THEME_CHOICES = [
        (THEME_AUTO, "Auto"),
        (THEME_LIGHT, "Light"),
        (THEME_DARK, "Dark"),
    ]
    BOOKMARK_DATE_DISPLAY_RELATIVE = "relative"
    BOOKMARK_DATE_DISPLAY_ABSOLUTE = "absolute"
    BOOKMARK_DATE_DISPLAY_HIDDEN = "hidden"
    BOOKMARK_DATE_DISPLAY_CHOICES = [
        (BOOKMARK_DATE_DISPLAY_RELATIVE, "Relative"),
        (BOOKMARK_DATE_DISPLAY_ABSOLUTE, "Absolute"),
        (BOOKMARK_DATE_DISPLAY_HIDDEN, "Hidden"),
    ]
    BOOKMARK_DESCRIPTION_DISPLAY_INLINE = "inline"
    BOOKMARK_DESCRIPTION_DISPLAY_SEPARATE = "separate"
    BOOKMARK_DESCRIPTION_DISPLAY_CHOICES = [
        (BOOKMARK_DESCRIPTION_DISPLAY_INLINE, "Inline"),
        (BOOKMARK_DESCRIPTION_DISPLAY_SEPARATE, "Separate"),
    ]
    BOOKMARK_LINK_TARGET_BLANK = "_blank"
    BOOKMARK_LINK_TARGET_SELF = "_self"
    BOOKMARK_LINK_TARGET_CHOICES = [
        (BOOKMARK_LINK_TARGET_BLANK, "New page"),
        (BOOKMARK_LINK_TARGET_SELF, "Same page"),
    ]
    WEB_ARCHIVE_INTEGRATION_DISABLED = "disabled"
    WEB_ARCHIVE_INTEGRATION_ENABLED = "enabled"
    WEB_ARCHIVE_INTEGRATION_CHOICES = [
        (WEB_ARCHIVE_INTEGRATION_DISABLED, "Disabled"),
        (WEB_ARCHIVE_INTEGRATION_ENABLED, "Enabled"),
    ]
    TAG_SEARCH_STRICT = "strict"
    TAG_SEARCH_LAX = "lax"
    TAG_SEARCH_CHOICES = [
        (TAG_SEARCH_STRICT, "Strict"),
        (TAG_SEARCH_LAX, "Lax"),
    ]
    TAG_GROUPING_ALPHABETICAL = "alphabetical"
    TAG_GROUPING_DISABLED = "disabled"
    TAG_GROUPING_CHOICES = [
        (TAG_GROUPING_ALPHABETICAL, "Alphabetical"),
        (TAG_GROUPING_DISABLED, "Disabled"),
    ]
    user = models.OneToOneField(
        get_user_model(), related_name="profile", on_delete=models.CASCADE
    )
    theme = models.CharField(
        max_length=10, choices=THEME_CHOICES, blank=False, default=THEME_AUTO
    )
    bookmark_date_display = models.CharField(
        max_length=10,
        choices=BOOKMARK_DATE_DISPLAY_CHOICES,
        blank=False,
        default=BOOKMARK_DATE_DISPLAY_RELATIVE,
    )
    bookmark_description_display = models.CharField(
        max_length=10,
        choices=BOOKMARK_DESCRIPTION_DISPLAY_CHOICES,
        blank=False,
        default=BOOKMARK_DESCRIPTION_DISPLAY_INLINE,
    )
    bookmark_description_max_lines = models.IntegerField(
        null=False,
        default=1,
    )
    bookmark_link_target = models.CharField(
        max_length=10,
        choices=BOOKMARK_LINK_TARGET_CHOICES,
        blank=False,
        default=BOOKMARK_LINK_TARGET_BLANK,
    )
    web_archive_integration = models.CharField(
        max_length=10,
        choices=WEB_ARCHIVE_INTEGRATION_CHOICES,
        blank=False,
        default=WEB_ARCHIVE_INTEGRATION_DISABLED,
    )
    tag_search = models.CharField(
        max_length=10,
        choices=TAG_SEARCH_CHOICES,
        blank=False,
        default=TAG_SEARCH_STRICT,
    )
    tag_grouping = models.CharField(
        max_length=12,
        choices=TAG_GROUPING_CHOICES,
        blank=False,
        default=TAG_GROUPING_ALPHABETICAL,
    )
    enable_sharing = models.BooleanField(default=False, null=False)
    enable_public_sharing = models.BooleanField(default=False, null=False)
    enable_favicons = models.BooleanField(default=False, null=False)
    enable_preview_images = models.BooleanField(default=False, null=False)
    display_url = models.BooleanField(default=False, null=False)
    display_view_bookmark_action = models.BooleanField(default=True, null=False)
    display_edit_bookmark_action = models.BooleanField(default=True, null=False)
    display_archive_bookmark_action = models.BooleanField(default=True, null=False)
    display_remove_bookmark_action = models.BooleanField(default=True, null=False)
    permanent_notes = models.BooleanField(default=False, null=False)
    custom_css = models.TextField(blank=True, null=False)
    custom_css_hash = models.CharField(blank=True, null=False, max_length=32)
    auto_tagging_rules = models.TextField(blank=True, null=False)
    search_preferences = models.JSONField(default=dict, null=False)
    enable_automatic_html_snapshots = models.BooleanField(default=True, null=False)
    default_mark_unread = models.BooleanField(default=False, null=False)
    items_per_page = models.IntegerField(
        null=False, default=30, validators=[MinValueValidator(10)]
    )
    sticky_pagination = models.BooleanField(default=False, null=False)

    def save(self, *args, **kwargs):
        if self.custom_css:
            self.custom_css_hash = hashlib.md5(
                self.custom_css.encode("utf-8")
            ).hexdigest()
        else:
            self.custom_css_hash = ""
        super().save(*args, **kwargs)


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            "theme",
            "bookmark_date_display",
            "bookmark_description_display",
            "bookmark_description_max_lines",
            "bookmark_link_target",
            "web_archive_integration",
            "tag_search",
            "tag_grouping",
            "enable_sharing",
            "enable_public_sharing",
            "enable_favicons",
            "enable_preview_images",
            "enable_automatic_html_snapshots",
            "display_url",
            "display_view_bookmark_action",
            "display_edit_bookmark_action",
            "display_archive_bookmark_action",
            "display_remove_bookmark_action",
            "permanent_notes",
            "default_mark_unread",
            "custom_css",
            "auto_tagging_rules",
            "items_per_page",
            "sticky_pagination",
        ]


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
    user = models.OneToOneField(
        get_user_model(),
        related_name="feed_token",
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


class GlobalSettings(models.Model):
    LANDING_PAGE_LOGIN = "login"
    LANDING_PAGE_SHARED_BOOKMARKS = "shared_bookmarks"
    LANDING_PAGE_CHOICES = [
        (LANDING_PAGE_LOGIN, "Login"),
        (LANDING_PAGE_SHARED_BOOKMARKS, "Shared Bookmarks"),
    ]

    landing_page = models.CharField(
        max_length=50,
        choices=LANDING_PAGE_CHOICES,
        blank=False,
        default=LANDING_PAGE_LOGIN,
    )
    guest_profile_user = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, null=True, blank=True
    )
    enable_link_prefetch = models.BooleanField(default=False, null=False)

    @classmethod
    def get(cls):
        instance = GlobalSettings.objects.first()
        if not instance:
            instance = GlobalSettings()
            instance.save()
        return instance

    def save(self, *args, **kwargs):
        if not self.pk and GlobalSettings.objects.exists():
            raise Exception("There is already one instance of GlobalSettings")
        return super(GlobalSettings, self).save(*args, **kwargs)


class GlobalSettingsForm(forms.ModelForm):
    class Meta:
        model = GlobalSettings
        fields = ["landing_page", "guest_profile_user", "enable_link_prefetch"]

    def __init__(self, *args, **kwargs):
        super(GlobalSettingsForm, self).__init__(*args, **kwargs)
        self.fields["guest_profile_user"].empty_label = "Standard profile"
