from django import forms
from django.template import Context, Template
from django.test import SimpleTestCase


class ExampleForm(forms.Form):
    theme = forms.CharField()


class FormLabelTagTestCase(SimpleTestCase):
    def render(self, label_text):
        template = Template("{% load shared %}{% formlabel form.theme label %}")
        context = Context({"form": ExampleForm(), "label": label_text})
        return template.render(context)

    def test_renders_label_for_field(self):
        html = self.render("Theme")

        self.assertEqual('<label for="id_theme" class="form-label">Theme</label>', html)

    def test_escapes_label_text(self):
        html = self.render("Theme <script>alert(1)</script>")

        self.assertEqual(
            '<label for="id_theme" class="form-label">'
            "Theme &lt;script&gt;alert(1)&lt;/script&gt;</label>",
            html,
        )
