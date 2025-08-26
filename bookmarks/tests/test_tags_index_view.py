from django.test import TestCase
from django.urls import reverse

from bookmarks.models import Tag
from bookmarks.tests.helpers import BookmarkFactoryMixin, HtmlTestMixin


class TagsIndexViewTestCase(TestCase, BookmarkFactoryMixin, HtmlTestMixin):
    def setUp(self) -> None:
        self.user = self.get_or_create_test_user()
        self.client.force_login(self.user)

    def get_rows(self, response):
        html = response.content.decode()
        soup = self.make_soup(html)
        return soup.select(".crud-table tbody tr")

    def find_row(self, rows, tag):
        for row in rows:
            if tag.name in row.get_text():
                return row
        return None

    def assertRows(self, response, tags):
        rows = self.get_rows(response)
        self.assertEqual(len(rows), len(tags))
        for tag in tags:
            row = self.find_row(rows, tag)
            self.assertIsNotNone(row, f"Tag '{tag.name}' not found in table")

    def assertOrderedRows(self, response, tags):
        rows = self.get_rows(response)
        self.assertEqual(len(rows), len(tags))
        for index, tag in enumerate(tags):
            row = rows[index]
            self.assertIn(
                tag.name,
                row.get_text(),
                f"Tag '{tag.name}' not found at index {index}",
            )

    def test_list_tags(self):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        tag3 = self.setup_tag()

        response = self.client.get(reverse("linkding:tags.index"))

        self.assertEqual(response.status_code, 200)
        self.assertRows(response, [tag1, tag2, tag3])

    def test_show_user_owned_tags(self):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        tag3 = self.setup_tag()

        other_user = self.setup_user()
        self.setup_tag(user=other_user)
        self.setup_tag(user=other_user)
        self.setup_tag(user=other_user)

        response = self.client.get(reverse("linkding:tags.index"))

        self.assertRows(response, [tag1, tag2, tag3])

    def test_search_tags(self):
        tag1 = self.setup_tag(name="programming")
        self.setup_tag(name="python")
        self.setup_tag(name="django")
        self.setup_tag(name="design")

        response = self.client.get(reverse("linkding:tags.index") + "?search=prog")

        self.assertRows(response, [tag1])

    def test_filter_unused_tags(self):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        tag3 = self.setup_tag()

        self.setup_bookmark(tags=[tag1])
        self.setup_bookmark(tags=[tag3])

        response = self.client.get(reverse("linkding:tags.index") + "?unused=true")

        self.assertRows(response, [tag2])

    def test_rows_have_links_to_filtered_bookmarks(self):
        tag1 = self.setup_tag(name="python")
        tag2 = self.setup_tag(name="django-framework")

        self.setup_bookmark(tags=[tag1])
        self.setup_bookmark(tags=[tag1, tag2])

        response = self.client.get(reverse("linkding:tags.index"))

        rows = self.get_rows(response)

        tag1_row = self.find_row(rows, tag1)
        view_link = tag1_row.find("a", string=lambda s: s and s.strip() == "2")
        expected_url = reverse("linkding:bookmarks.index") + "?q=%23python"
        self.assertEqual(view_link["href"], expected_url)

        tag2_row = self.find_row(rows, tag2)
        view_link = tag2_row.find("a", string=lambda s: s and s.strip() == "1")
        expected_url = reverse("linkding:bookmarks.index") + "?q=%23django-framework"
        self.assertEqual(view_link["href"], expected_url)

    def test_shows_tag_total(self):
        tag1 = self.setup_tag(name="python")
        tag2 = self.setup_tag(name="javascript")
        tag3 = self.setup_tag(name="design")
        self.setup_tag(name="unused-tag")

        self.setup_bookmark(tags=[tag1])
        self.setup_bookmark(tags=[tag2])
        self.setup_bookmark(tags=[tag3])

        response = self.client.get(reverse("linkding:tags.index"))
        self.assertContains(response, "4 tags total")

        response = self.client.get(reverse("linkding:tags.index") + "?search=python")
        self.assertContains(response, "Showing 1 of 4 tags")

        response = self.client.get(reverse("linkding:tags.index") + "?unused=true")
        self.assertContains(response, "Showing 1 of 4 tags")

        response = self.client.get(
            reverse("linkding:tags.index") + "?search=nonexistent"
        )
        self.assertContains(response, "Showing 0 of 4 tags")

    def test_pagination(self):
        tags = []
        for i in range(75):
            tags.append(self.setup_tag())

        response = self.client.get(reverse("linkding:tags.index"))
        rows = self.get_rows(response)
        self.assertEqual(len(rows), 50)

        response = self.client.get(reverse("linkding:tags.index") + "?page=2")
        rows = self.get_rows(response)
        self.assertEqual(len(rows), 25)

    def test_delete_action(self):
        tag = self.setup_tag(name="tag_to_delete")

        response = self.client.post(
            reverse("linkding:tags.index"), {"delete_tag": tag.id}
        )

        self.assertRedirects(response, reverse("linkding:tags.index"))
        self.assertFalse(Tag.objects.filter(id=tag.id).exists())

    def test_tag_delete_action_shows_success_message(self):
        tag = self.setup_tag(name="tag_to_delete")

        response = self.client.post(
            reverse("linkding:tags.index"), {"delete_tag": tag.id}, follow=True
        )

        self.assertEqual(response.status_code, 200)

        self.assertInHTML(
            """
            <div class="toast toast-success" role="alert">
                Tag "tag_to_delete" deleted successfully.
            </div>
        """,
            response.content.decode(),
        )

    def test_tag_delete_action_preserves_query_parameters(self):
        tag = self.setup_tag(name="search_tag")

        url = (
            reverse("linkding:tags.index")
            + "?search=search&unused=true&page=2&sort=name-desc"
        )
        response = self.client.post(url, {"delete_tag": tag.id})

        self.assertRedirects(response, url)

    def test_tag_delete_action_only_deletes_own_tags(self):
        other_user = self.setup_user()
        other_tag = self.setup_tag(user=other_user, name="other_user_tag")

        response = self.client.post(
            reverse("linkding:tags.index"), {"delete_tag": other_tag.id}, follow=True
        )

        self.assertEqual(response.status_code, 404)

    def test_sort_by_name_ascending(self):
        tag_c = self.setup_tag(name="c_tag")
        tag_a = self.setup_tag(name="a_tag")
        tag_b = self.setup_tag(name="b_tag")

        response = self.client.get(reverse("linkding:tags.index") + "?sort=name-asc")

        self.assertOrderedRows(response, [tag_a, tag_b, tag_c])

    def test_sort_by_name_descending(self):
        tag_c = self.setup_tag(name="c_tag")
        tag_a = self.setup_tag(name="a_tag")
        tag_b = self.setup_tag(name="b_tag")

        response = self.client.get(reverse("linkding:tags.index") + "?sort=name-desc")

        self.assertOrderedRows(response, [tag_c, tag_b, tag_a])

    def test_sort_by_bookmark_count_ascending(self):
        tag_few = self.setup_tag(name="few_bookmarks")
        tag_many = self.setup_tag(name="many_bookmarks")
        tag_none = self.setup_tag(name="no_bookmarks")

        self.setup_bookmark(tags=[tag_few])
        self.setup_bookmark(tags=[tag_many])
        self.setup_bookmark(tags=[tag_many])
        self.setup_bookmark(tags=[tag_many])

        response = self.client.get(reverse("linkding:tags.index") + "?sort=count-asc")

        self.assertOrderedRows(response, [tag_none, tag_few, tag_many])

    def test_sort_by_bookmark_count_descending(self):
        tag_few = self.setup_tag(name="few_bookmarks")
        tag_many = self.setup_tag(name="many_bookmarks")
        tag_none = self.setup_tag(name="no_bookmarks")

        self.setup_bookmark(tags=[tag_few])
        self.setup_bookmark(tags=[tag_many])
        self.setup_bookmark(tags=[tag_many])
        self.setup_bookmark(tags=[tag_many])

        response = self.client.get(reverse("linkding:tags.index") + "?sort=count-desc")

        self.assertOrderedRows(response, [tag_many, tag_few, tag_none])

    def test_default_sort_is_name_ascending(self):
        tag_c = self.setup_tag(name="c_tag")
        tag_a = self.setup_tag(name="a_tag")
        tag_b = self.setup_tag(name="b_tag")

        response = self.client.get(reverse("linkding:tags.index"))

        self.assertOrderedRows(response, [tag_a, tag_b, tag_c])

    def test_sort_select_has_correct_options_and_selection(self):
        self.setup_tag()

        response = self.client.get(reverse("linkding:tags.index"))
        html = response.content.decode()

        self.assertInHTML(
            """
            <select id="sort" name="sort" class="form-select" ld-auto-submit>
              <option value="name-asc" selected>Name A-Z</option>
              <option value="name-desc">Name Z-A</option>
              <option value="count-asc">Fewest bookmarks</option>
              <option value="count-desc">Most bookmarks</option>
            </select>        
        """,
            html,
        )

        response = self.client.get(reverse("linkding:tags.index") + "?sort=name-desc")
        html = response.content.decode()

        self.assertInHTML(
            """
            <select id="sort" name="sort" class="form-select" ld-auto-submit>
              <option value="name-asc">Name A-Z</option>
              <option value="name-desc" selected>Name Z-A</option>
              <option value="count-asc">Fewest bookmarks</option>
              <option value="count-desc">Most bookmarks</option>
            </select>        
        """,
            html,
        )
