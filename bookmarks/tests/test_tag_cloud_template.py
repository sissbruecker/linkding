from typing import List, Type

from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpResponse
from django.template import Template, RequestContext
from django.test import TestCase, RequestFactory

from bookmarks.middlewares import LinkdingMiddleware
from bookmarks.models import UserProfile
from bookmarks.tests.helpers import BookmarkFactoryMixin, HtmlTestMixin
from bookmarks.views import contexts


class TagCloudTemplateTest(TestCase, BookmarkFactoryMixin, HtmlTestMixin):
    def render_template(
        self,
        context_type: Type[contexts.TagCloudContext] = contexts.ActiveTagCloudContext,
        url: str = "/test",
        user: User | AnonymousUser = None,
    ):
        rf = RequestFactory()
        request = rf.get(url)
        request.user = user or self.get_or_create_test_user()
        middleware = LinkdingMiddleware(lambda r: HttpResponse())
        middleware(request)

        tag_cloud_context = context_type(request)
        context = RequestContext(request, {"tag_cloud": tag_cloud_context})
        template_to_render = Template("{% include 'bookmarks/tag_cloud.html' %}")
        return template_to_render.render(context)

    def assertTagGroups(self, rendered_template: str, groups: List[List[str]]):
        soup = self.make_soup(rendered_template)
        group_elements = soup.select("p.group")

        self.assertEqual(len(group_elements), len(groups))

        for group_index, tags in enumerate(groups, start=0):
            group_element = group_elements[group_index]
            link_elements = group_element.select("a")

            self.assertEqual(len(link_elements), len(tags), tags)

            for tag_index, tag in enumerate(tags, start=0):
                link_element = link_elements[tag_index]
                self.assertEqual(link_element.text.strip(), tag)

    def assertNumSelectedTags(self, rendered_template: str, count: int):
        soup = self.make_soup(rendered_template)
        link_elements = soup.select("p.selected-tags a")
        self.assertEqual(len(link_elements), count)

    def test_cjk_using_single_group(self):
        """
        Ideographic characters will be using the same group
        While other japanese and korean characters will have separate groups.
        """
        tags = [
            self.setup_tag(name="Aardvark"),
            self.setup_tag(name="Armadillo"),
            self.setup_tag(name="あひる"),
            self.setup_tag(name="あきらか"),
            self.setup_tag(name="アヒル"),
            self.setup_tag(name="アキラカ"),
            self.setup_tag(name="ひる"),
            self.setup_tag(name="アヒル"),
            self.setup_tag(name="오리"),
            self.setup_tag(name="물"),
            self.setup_tag(name="家鴨"),
            self.setup_tag(name="感じ"),
        ]
        self.setup_bookmark(tags=tags)
        rendered_template = self.render_template()

        self.assertTagGroups(
            rendered_template,
            [
                [
                    "Aardvark",
                    "Armadillo",
                ],
                [
                    "あきらか",
                    "あひる",
                ],
                [
                    "ひる",
                ],
                [
                    "アキラカ",
                    "アヒル",
                ],
                [
                    "물",
                ],
                [
                    "오리",
                ],
                [
                    "家鴨",
                    "感じ",
                ],
            ],
        )

    def test_group_alphabetically(self):
        tags = [
            self.setup_tag(name="Cockatoo"),
            self.setup_tag(name="Badger"),
            self.setup_tag(name="Buffalo"),
            self.setup_tag(name="Chihuahua"),
            self.setup_tag(name="Alpaca"),
            self.setup_tag(name="Coyote"),
            self.setup_tag(name="Aardvark"),
            self.setup_tag(name="Bumblebee"),
            self.setup_tag(name="Armadillo"),
        ]
        self.setup_bookmark(tags=tags)

        rendered_template = self.render_template()

        self.assertTagGroups(
            rendered_template,
            [
                [
                    "Aardvark",
                    "Alpaca",
                    "Armadillo",
                ],
                [
                    "Badger",
                    "Buffalo",
                    "Bumblebee",
                ],
                [
                    "Chihuahua",
                    "Cockatoo",
                    "Coyote",
                ],
            ],
        )

    def test_group_when_grouping_disabled(self):
        profile = self.get_or_create_test_user().profile
        profile.tag_grouping = UserProfile.TAG_GROUPING_DISABLED
        profile.save()

        tags = [
            self.setup_tag(name="Cockatoo"),
            self.setup_tag(name="Badger"),
            self.setup_tag(name="Buffalo"),
            self.setup_tag(name="Chihuahua"),
            self.setup_tag(name="Alpaca"),
            self.setup_tag(name="Coyote"),
            self.setup_tag(name="Aardvark"),
            self.setup_tag(name="Bumblebee"),
            self.setup_tag(name="Armadillo"),
        ]
        self.setup_bookmark(tags=tags)

        rendered_template = self.render_template()

        self.assertTagGroups(
            rendered_template,
            [
                [
                    "Aardvark",
                    "Alpaca",
                    "Armadillo",
                    "Badger",
                    "Buffalo",
                    "Bumblebee",
                    "Chihuahua",
                    "Cockatoo",
                    "Coyote",
                ],
            ],
        )

    def test_no_duplicate_tag_names(self):
        tags = [
            self.setup_tag(name="shared", user=self.setup_user(enable_sharing=True)),
            self.setup_tag(name="shared", user=self.setup_user(enable_sharing=True)),
            self.setup_tag(name="shared", user=self.setup_user(enable_sharing=True)),
        ]
        for tag in tags:
            self.setup_bookmark(tags=[tag], user=tag.owner, shared=True)

        rendered_template = self.render_template(
            context_type=contexts.SharedTagCloudContext
        )

        self.assertTagGroups(
            rendered_template,
            [
                [
                    "shared",
                ],
            ],
        )

    def test_tag_url_respects_search_options(self):
        tag = self.setup_tag(name="tag1")
        self.setup_bookmark(tags=[tag], title="term1")

        rendered_template = self.render_template(url="/test?q=term1&sort=title_asc")

        self.assertInHTML(
            """
            <a href="?q=term1+%23tag1&sort=title_asc" class="mr-2" data-is-tag-item>
              <span class="highlight-char">t</span><span>ag1</span>
            </a>
        """,
            rendered_template,
        )

    def test_tag_url_removes_page_number_and_details_id(self):
        tag = self.setup_tag(name="tag1")
        self.setup_bookmark(tags=[tag], title="term1")

        rendered_template = self.render_template(
            url="/test?q=term1&sort=title_asc&page=2&details=5"
        )

        self.assertInHTML(
            """
            <a href="?q=term1+%23tag1&sort=title_asc" class="mr-2" data-is-tag-item>
              <span class="highlight-char">t</span><span>ag1</span>
            </a>
        """,
            rendered_template,
        )

    def test_selected_tags(self):
        tags = [
            self.setup_tag(name="tag1"),
            self.setup_tag(name="tag2"),
        ]
        self.setup_bookmark(tags=tags)

        rendered_template = self.render_template(url="/test?q=%23tag1 %23tag2")

        self.assertNumSelectedTags(rendered_template, 2)

        self.assertInHTML(
            """
            <a href="?q=%23tag2"
               class="text-bold mr-2">
                <span>-tag1</span>
            </a>
        """,
            rendered_template,
        )

        self.assertInHTML(
            """
            <a href="?q=%23tag1"
               class="text-bold mr-2">
                <span>-tag2</span>
            </a>
        """,
            rendered_template,
        )

    def test_selected_tags_with_lax_tag_search(self):
        profile = self.get_or_create_test_user().profile
        profile.tag_search = UserProfile.TAG_SEARCH_LAX
        profile.save()

        tags = [
            self.setup_tag(name="tag1"),
            self.setup_tag(name="tag2"),
        ]
        self.setup_bookmark(tags=tags)

        # Filter by tag name without hash
        rendered_template = self.render_template(url="/test?q=tag1 %23tag2")

        self.assertNumSelectedTags(rendered_template, 2)

        # Tag name should still be removed from query string
        self.assertInHTML(
            """
            <a href="?q=%23tag2"
               class="text-bold mr-2">
                <span>-tag1</span>
            </a>
        """,
            rendered_template,
        )

        self.assertInHTML(
            """
            <a href="?q=tag1"
               class="text-bold mr-2">
                <span>-tag2</span>
            </a>
        """,
            rendered_template,
        )

    def test_selected_tags_ignore_casing_when_removing_query_part(self):
        tags = [
            self.setup_tag(name="TEST"),
        ]
        self.setup_bookmark(tags=tags)

        rendered_template = self.render_template(url="/test?q=%23test")

        self.assertInHTML(
            """
            <a href="?q="
               class="text-bold mr-2">
                <span>-TEST</span>
            </a>
        """,
            rendered_template,
        )

    def test_no_duplicate_selected_tags(self):
        tags = [
            self.setup_tag(name="shared", user=self.setup_user(enable_sharing=True)),
            self.setup_tag(name="shared", user=self.setup_user(enable_sharing=True)),
            self.setup_tag(name="shared", user=self.setup_user(enable_sharing=True)),
        ]
        for tag in tags:
            self.setup_bookmark(tags=[tag], shared=True, user=tag.owner)

        rendered_template = self.render_template(
            context_type=contexts.SharedTagCloudContext, url="/test?q=%23shared"
        )

        self.assertInHTML(
            """
            <a href="?q="
               class="text-bold mr-2">
                <span>-shared</span>
            </a>
        """,
            rendered_template,
            count=1,
        )

    def test_selected_tag_url_keeps_other_query_terms(self):
        tag = self.setup_tag(name="tag1")
        self.setup_bookmark(tags=[tag], title="term1", description="term2")

        rendered_template = self.render_template(url="/test?q=term1 %23tag1 term2")

        self.assertInHTML(
            """
            <a href="?q=term1+term2"
               class="text-bold mr-2">
                <span>-tag1</span>
            </a>
        """,
            rendered_template,
        )

    def test_selected_tag_url_respects_search_options(self):
        tag = self.setup_tag(name="tag1")
        self.setup_bookmark(tags=[tag], title="term1", description="term2")

        rendered_template = self.render_template(
            url="/test?q=term1 %23tag1 term2&sort=title_asc"
        )

        self.assertInHTML(
            """
            <a href="?q=term1+term2&sort=title_asc"
               class="text-bold mr-2">
                <span>-tag1</span>
            </a>
        """,
            rendered_template,
        )

    def test_selected_tag_url_removes_page_number_and_details_id(self):
        tag = self.setup_tag(name="tag1")
        self.setup_bookmark(tags=[tag], title="term1", description="term2")

        rendered_template = self.render_template(
            url="/test?q=term1 %23tag1 term2&sort=title_asc&page=2&details=5"
        )

        self.assertInHTML(
            """
            <a href="?q=term1+term2&sort=title_asc"
               class="text-bold mr-2">
                <span>-tag1</span>
            </a>
        """,
            rendered_template,
        )

    def test_selected_tags_are_excluded_from_groups(self):
        tags = [
            self.setup_tag(name="tag1"),
            self.setup_tag(name="tag2"),
            self.setup_tag(name="tag3"),
            self.setup_tag(name="tag4"),
            self.setup_tag(name="tag5"),
        ]
        self.setup_bookmark(tags=tags)

        rendered_template = self.render_template(url="/test?q=%23tag1 %23tag2")

        self.assertTagGroups(rendered_template, [["tag3", "tag4", "tag5"]])

    def test_with_anonymous_user(self):
        profile = self.get_or_create_test_user().profile
        profile.enable_sharing = True
        profile.enable_public_sharing = True
        profile.save()

        tags = [
            self.setup_tag(name="tag1"),
            self.setup_tag(name="tag2"),
            self.setup_tag(name="tag3"),
            self.setup_tag(name="tag4"),
            self.setup_tag(name="tag5"),
        ]
        self.setup_bookmark(tags=tags, shared=True)

        rendered_template = self.render_template(
            context_type=contexts.SharedTagCloudContext,
            url="/test?q=%23tag1 %23tag2",
            user=AnonymousUser(),
        )

        self.assertTagGroups(rendered_template, [["tag3", "tag4", "tag5"]])
        self.assertNumSelectedTags(rendered_template, 2)
        self.assertInHTML(
            """
            <a href="?q=%23tag2"
               class="text-bold mr-2">
                <span>-tag1</span>
            </a>
        """,
            rendered_template,
        )

        self.assertInHTML(
            """
            <a href="?q=%23tag1"
               class="text-bold mr-2">
                <span>-tag2</span>
            </a>
        """,
            rendered_template,
        )
