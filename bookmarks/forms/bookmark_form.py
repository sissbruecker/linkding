from django import forms

from ..models import Bookmark

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
