from django import forms
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from bookmarks.models import (
    Bookmark,
    BookmarkBundle,
    BookmarkSearch,
    GlobalSettings,
    Tag,
    UserProfile,
    build_tag_string,
    parse_tag_string,
    sanitize_tag_name,
)
from bookmarks.services.bookmarks import create_bookmark, update_bookmark
from bookmarks.type_defs import HttpRequest
from bookmarks.validators import BookmarkURLValidator
from bookmarks.widgets import (
    FormCheckbox,
    FormErrorList,
    FormInput,
    FormNumberInput,
    FormSelect,
    FormTextarea,
    TagAutocomplete,
)


class BookmarkForm(forms.ModelForm):
    # Use URLField for URL
    url = forms.CharField(validators=[BookmarkURLValidator()], widget=FormInput)
    tag_string = forms.CharField(required=False, widget=TagAutocomplete)
    # Do not require title and description as they may be empty
    title = forms.CharField(max_length=512, required=False, widget=FormInput)
    description = forms.CharField(required=False, widget=FormTextarea)
    notes = forms.CharField(required=False, widget=FormTextarea)
    unread = forms.BooleanField(required=False, widget=FormCheckbox)
    shared = forms.BooleanField(required=False, widget=FormCheckbox)
    # Hidden field that determines whether to close window/tab after saving the bookmark
    auto_close = forms.CharField(required=False, widget=forms.HiddenInput)

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

    def __init__(self, request: HttpRequest, instance: Bookmark = None):
        self.request = request

        initial = None
        if instance is None and request.method == "GET":
            initial = {
                "url": request.GET.get("url"),
                "title": request.GET.get("title"),
                "description": request.GET.get("description"),
                "notes": request.GET.get("notes"),
                "tag_string": request.GET.get("tags"),
                "auto_close": "auto_close" in request.GET,
                "unread": request.user_profile.default_mark_unread,
                "shared": request.user_profile.default_mark_shared,
            }
        if instance is not None and request.method == "GET":
            initial = {"tag_string": build_tag_string(instance.tag_names, " ")}
        data = request.POST if request.method == "POST" else None
        super().__init__(
            data, instance=instance, initial=initial, error_class=FormErrorList
        )

    @property
    def is_auto_close(self):
        return self.data.get("auto_close", False) == "True" or self.initial.get(
            "auto_close", False
        )

    @property
    def has_notes(self):
        return self.initial.get("notes", None) or (
            self.instance and self.instance.notes
        )

    def save(self, commit=False):
        tag_string = convert_tag_string(self.data["tag_string"])
        bookmark = super().save(commit=False)
        if self.instance.pk:
            return update_bookmark(bookmark, tag_string, self.request.user)
        else:
            return create_bookmark(bookmark, tag_string, self.request.user)

    def clean_url(self):
        # When creating a bookmark, the service logic prevents duplicate URLs by
        # updating the existing bookmark instead, which is also communicated in
        # the form's UI. When editing a bookmark, there is no assumption that
        # it would update a different bookmark if the URL is a duplicate, so
        # raise a validation error in that case.
        url = self.cleaned_data["url"]
        if self.instance.pk:
            is_duplicate = (
                Bookmark.query_existing(self.instance.owner, url)
                .exclude(pk=self.instance.pk)
                .exists()
            )
            if is_duplicate:
                raise forms.ValidationError("A bookmark with this URL already exists.")

        return url


def convert_tag_string(tag_string: str):
    # Tag strings coming from inputs are space-separated, however services.bookmarks functions expect comma-separated
    # strings
    return tag_string.replace(" ", ",")


class TagForm(forms.ModelForm):
    name = forms.CharField(widget=FormInput)

    class Meta:
        model = Tag
        fields = ["name"]

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs, error_class=FormErrorList)
        self.user = user

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()

        name = sanitize_tag_name(name)

        queryset = Tag.objects.filter(name__iexact=name, owner=self.user)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError(f'Tag "{name}" already exists.')

        return name

    def save(self, commit=True):
        tag = super().save(commit=False)
        if not self.instance.pk:
            tag.owner = self.user
            tag.date_added = timezone.now()
        else:
            tag.date_modified = timezone.now()
        if commit:
            tag.save()
        return tag


class TagMergeForm(forms.Form):
    target_tag = forms.CharField(widget=TagAutocomplete)
    merge_tags = forms.CharField(widget=TagAutocomplete)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs, error_class=FormErrorList)
        self.user = user

    def clean_target_tag(self):
        target_tag_name = self.cleaned_data.get("target_tag", "")

        target_tag_names = parse_tag_string(target_tag_name, " ")
        if len(target_tag_names) != 1:
            raise forms.ValidationError(
                "Please enter only one tag name for the target tag."
            )

        target_tag_name = target_tag_names[0]

        try:
            target_tag = Tag.objects.get(name__iexact=target_tag_name, owner=self.user)
        except Tag.DoesNotExist:
            raise forms.ValidationError(
                f'Tag "{target_tag_name}" does not exist.'
            ) from None

        return target_tag

    def clean_merge_tags(self):
        merge_tags_string = self.cleaned_data.get("merge_tags", "")

        merge_tag_names = parse_tag_string(merge_tags_string, " ")
        if not merge_tag_names:
            raise forms.ValidationError("Please enter at least one tag to merge.")

        merge_tags = []
        for tag_name in merge_tag_names:
            try:
                tag = Tag.objects.get(name__iexact=tag_name, owner=self.user)
                merge_tags.append(tag)
            except Tag.DoesNotExist:
                raise forms.ValidationError(
                    f'Tag "{tag_name}" does not exist.'
                ) from None

        target_tag = self.cleaned_data.get("target_tag")
        if target_tag and target_tag in merge_tags:
            raise forms.ValidationError(
                "The target tag cannot be selected for merging."
            )

        return merge_tags


class BookmarkBundleForm(forms.ModelForm):
    name = forms.CharField(max_length=256, widget=FormInput)
    search = forms.CharField(max_length=256, required=False, widget=FormInput)
    any_tags = forms.CharField(required=False, widget=TagAutocomplete)
    all_tags = forms.CharField(required=False, widget=TagAutocomplete)
    excluded_tags = forms.CharField(required=False, widget=TagAutocomplete)

    class Meta:
        model = BookmarkBundle
        fields = ["name", "search", "any_tags", "all_tags", "excluded_tags"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, error_class=FormErrorList)


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
    user = forms.ChoiceField(required=False, widget=FormSelect)
    bundle = forms.CharField(required=False)
    sort = forms.ChoiceField(choices=SORT_CHOICES, widget=FormSelect)
    shared = forms.ChoiceField(choices=FILTER_SHARED_CHOICES, widget=forms.RadioSelect)
    unread = forms.ChoiceField(choices=FILTER_UNREAD_CHOICES, widget=forms.RadioSelect)
    modified_since = forms.CharField(required=False)
    added_since = forms.CharField(required=False)

    def __init__(
        self,
        search: BookmarkSearch,
        editable_fields: list[str] = None,
        users: list[User] = None,
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
            value = search.__dict__.get(param)
            if isinstance(value, models.Model):
                self.fields[param].initial = value.id
            else:
                self.fields[param].initial = value

            # Mark non-editable modified fields as hidden. That way, templates
            # rendering a form can just loop over hidden_fields to ensure that
            # all necessary search options are kept when submitting the form.
            if search.is_modified(param) and param not in editable_fields:
                self.fields[param].widget = forms.HiddenInput()


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
            "default_mark_shared",
            "custom_css",
            "auto_tagging_rules",
            "items_per_page",
            "sticky_pagination",
            "collapse_side_panel",
            "hide_bundles",
            "legacy_search",
        ]
        widgets = {
            "theme": FormSelect,
            "bookmark_date_display": FormSelect,
            "bookmark_description_display": FormSelect,
            "bookmark_description_max_lines": FormNumberInput,
            "bookmark_link_target": FormSelect,
            "web_archive_integration": FormSelect,
            "tag_search": FormSelect,
            "tag_grouping": FormSelect,
            "auto_tagging_rules": FormTextarea,
            "custom_css": FormTextarea,
            "items_per_page": FormNumberInput,
            "display_url": FormCheckbox,
            "permanent_notes": FormCheckbox,
            "display_view_bookmark_action": FormCheckbox,
            "display_edit_bookmark_action": FormCheckbox,
            "display_archive_bookmark_action": FormCheckbox,
            "display_remove_bookmark_action": FormCheckbox,
            "sticky_pagination": FormCheckbox,
            "collapse_side_panel": FormCheckbox,
            "hide_bundles": FormCheckbox,
            "legacy_search": FormCheckbox,
            "enable_favicons": FormCheckbox,
            "enable_preview_images": FormCheckbox,
            "enable_sharing": FormCheckbox,
            "enable_public_sharing": FormCheckbox,
            "enable_automatic_html_snapshots": FormCheckbox,
            "default_mark_unread": FormCheckbox,
            "default_mark_shared": FormCheckbox,
        }


class GlobalSettingsForm(forms.ModelForm):
    class Meta:
        model = GlobalSettings
        fields = ["landing_page", "guest_profile_user", "enable_link_prefetch"]
        widgets = {
            "landing_page": FormSelect,
            "guest_profile_user": FormSelect,
            "enable_link_prefetch": FormCheckbox,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["guest_profile_user"].empty_label = "Standard profile"
