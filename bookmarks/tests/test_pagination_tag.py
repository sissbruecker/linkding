from django.core.paginator import Paginator
from django.template import Template, RequestContext
from django.test import TestCase, RequestFactory

from bookmarks.tests.helpers import BookmarkFactoryMixin


class PaginationTagTest(TestCase, BookmarkFactoryMixin):

    def render_template(
        self, num_items: int, page_size: int, current_page: int, url: str = "/test"
    ) -> str:
        rf = RequestFactory()
        request = rf.get(url)
        request.user = self.get_or_create_test_user()
        request.user_profile = self.get_or_create_test_user().profile
        paginator = Paginator(range(0, num_items), page_size)
        page = paginator.page(current_page)

        context = RequestContext(request, {"page": page})
        template_to_render = Template("{% load pagination %}" "{% pagination page %}")
        return template_to_render.render(context)

    def assertPrevLinkDisabled(self, html: str):
        self.assertInHTML(
            """
            <li class="page-item disabled">
                <a href="#" tabindex="-1">Previous</a>
            </li>
            """,
            html,
        )

    def assertPrevLink(self, html: str, page_number: int, href: str = None):
        href = href if href else "?page={0}".format(page_number)
        self.assertInHTML(
            """
            <li class="page-item">
                <a href="{0}" tabindex="-1">Previous</a>
            </li>
            """.format(
                href
            ),
            html,
        )

    def assertNextLinkDisabled(self, html: str):
        self.assertInHTML(
            """
            <li class="page-item disabled">
                <a href="#" tabindex="-1">Next</a>
            </li>
            """,
            html,
        )

    def assertNextLink(self, html: str, page_number: int, href: str = None):
        href = href if href else "?page={0}".format(page_number)
        self.assertInHTML(
            """
            <li class="page-item">
                <a href="{0}" tabindex="-1">Next</a>
            </li>
            """.format(
                href
            ),
            html,
        )

    def assertPageLink(
        self,
        html: str,
        page_number: int,
        active: bool,
        count: int = 1,
        href: str = None,
    ):
        active_class = "active" if active else ""
        href = href if href else "?page={0}".format(page_number)
        self.assertInHTML(
            """
            <li class="page-item {1}">
                <a href="{2}">{0}</a>
            </li>
            """.format(
                page_number, active_class, href
            ),
            html,
            count=count,
        )

    def assertTruncationIndicators(self, html: str, count: int):
        self.assertInHTML(
            """
            <li class="page-item">
                <span>...</span>
            </li>
            """,
            html,
            count=count,
        )

    def test_previous_disabled_on_page_1(self):
        rendered_template = self.render_template(100, 10, 1)
        self.assertPrevLinkDisabled(rendered_template)

    def test_previous_enabled_after_page_1(self):
        for page_number in range(2, 10):
            rendered_template = self.render_template(100, 10, page_number)
            self.assertPrevLink(rendered_template, page_number - 1)

    def test_next_disabled_on_last_page(self):
        rendered_template = self.render_template(100, 10, 10)
        self.assertNextLinkDisabled(rendered_template)

    def test_next_enabled_before_last_page(self):
        for page_number in range(1, 9):
            rendered_template = self.render_template(100, 10, page_number)
            self.assertNextLink(rendered_template, page_number + 1)

    def test_truncate_pages_start(self):
        current_page = 1
        expected_visible_pages = [1, 2, 3, 10]
        rendered_template = self.render_template(100, 10, current_page)
        for page_number in range(1, 10):
            expected_occurrences = 1 if page_number in expected_visible_pages else 0
            self.assertPageLink(
                rendered_template,
                page_number,
                page_number == current_page,
                expected_occurrences,
            )
        self.assertTruncationIndicators(rendered_template, 1)

    def test_truncate_pages_middle(self):
        current_page = 5
        expected_visible_pages = [1, 3, 4, 5, 6, 7, 10]
        rendered_template = self.render_template(100, 10, current_page)
        for page_number in range(1, 10):
            expected_occurrences = 1 if page_number in expected_visible_pages else 0
            self.assertPageLink(
                rendered_template,
                page_number,
                page_number == current_page,
                expected_occurrences,
            )
        self.assertTruncationIndicators(rendered_template, 2)

    def test_truncate_pages_near_end(self):
        current_page = 9
        expected_visible_pages = [1, 7, 8, 9, 10]
        rendered_template = self.render_template(100, 10, current_page)
        for page_number in range(1, 10):
            expected_occurrences = 1 if page_number in expected_visible_pages else 0
            self.assertPageLink(
                rendered_template,
                page_number,
                page_number == current_page,
                expected_occurrences,
            )
        self.assertTruncationIndicators(rendered_template, 1)

    def test_respects_search_parameters(self):
        rendered_template = self.render_template(
            100, 10, 2, url="/test?q=cake&sort=title_asc&page=2"
        )
        self.assertPrevLink(rendered_template, 1, href="?q=cake&sort=title_asc&page=1")
        self.assertPageLink(
            rendered_template, 1, False, href="?q=cake&sort=title_asc&page=1"
        )
        self.assertPageLink(
            rendered_template, 2, True, href="?q=cake&sort=title_asc&page=2"
        )
        self.assertNextLink(rendered_template, 3, href="?q=cake&sort=title_asc&page=3")

    def test_removes_details_parameter(self):
        rendered_template = self.render_template(
            100, 10, 2, url="/test?details=1&page=2"
        )
        self.assertPrevLink(rendered_template, 1, href="?page=1")
        self.assertPageLink(rendered_template, 1, False, href="?page=1")
        self.assertPageLink(rendered_template, 2, True, href="?page=2")
        self.assertNextLink(rendered_template, 3, href="?page=3")
