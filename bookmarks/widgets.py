from django import forms
from django.forms.utils import ErrorList
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe


class FormErrorList(ErrorList):
    template_name = "shared/error_list.html"


class FormInput(forms.TextInput):
    def __init__(self, attrs=None):
        default_attrs = {"class": "form-input", "autocomplete": "off"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)


class FormNumberInput(forms.NumberInput):
    def __init__(self, attrs=None):
        default_attrs = {"class": "form-input"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)


class FormSelect(forms.Select):
    def __init__(self, attrs=None):
        default_attrs = {"class": "form-select"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)


class FormTextarea(forms.Textarea):
    def __init__(self, attrs=None):
        default_attrs = {"class": "form-input"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)


class FormCheckbox(forms.CheckboxInput):
    def __init__(self, attrs=None):
        super().__init__(attrs)
        self.label = "Label"

    def render(self, name, value, attrs=None, renderer=None):
        checkbox_html = super().render(name, value, attrs, renderer)
        input_id = attrs.get("id") if attrs else None
        return format_html(
            '<div class="form-checkbox">'
            "{}"
            '<i class="form-icon"></i>'
            '<label for="{}">{}</label>'
            "</div>",
            checkbox_html,
            input_id,
            self.label,
        )


class TagAutocomplete(forms.TextInput):
    def __init__(self, attrs=None):
        super().__init__(attrs)

    def render(self, name, value, attrs=None, renderer=None):
        # Merge self.attrs with passed attrs
        final_attrs = self.build_attrs(self.attrs, attrs)

        input_id = final_attrs.get("id")
        input_value = escape(value) if value else ""
        aria_describedby = final_attrs.get("aria-describedby")
        input_class = final_attrs.get("class")

        html = f'<ld-tag-autocomplete input-id="{input_id}" input-name="{name}" input-value="{input_value}"'
        if aria_describedby:
            html += f' input-aria-describedby="{aria_describedby}"'
        if input_class:
            html += f' input-class="{input_class}"'
        html += "></ld-tag-autocomplete>"

        return mark_safe(html)
