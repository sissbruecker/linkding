import operator

from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.test import TestCase

from bookmarks import queries
from bookmarks.models import Bookmark
from bookmarks.tests.helpers import BookmarkFactoryMixin, random_sentence
from bookmarks.utils import unique

User = get_user_model()


class QueriesTestCase(TestCase, BookmarkFactoryMixin):

    def setup_bookmark_search_data(self) -> None:
        tag1 = self.setup_tag(name='tag1')
        tag2 = self.setup_tag(name='tag2')
        self.setup_tag(name='unused_tag1')

        self.other_bookmarks = [
            self.setup_bookmark(),
            self.setup_bookmark(),
            self.setup_bookmark(),
        ]
        self.term1_bookmarks = [
            self.setup_bookmark(url='http://example.com/term1'),
            self.setup_bookmark(title=random_sentence(including_word='term1')),
            self.setup_bookmark(description=random_sentence(including_word='term1')),
            self.setup_bookmark(website_title=random_sentence(including_word='term1')),
            self.setup_bookmark(website_description=random_sentence(including_word='term1')),
        ]
        self.term1_term2_bookmarks = [
            self.setup_bookmark(url='http://example.com/term1/term2'),
            self.setup_bookmark(title=random_sentence(including_word='term1'),
                                description=random_sentence(including_word='term2')),
            self.setup_bookmark(description=random_sentence(including_word='term1'),
                                title=random_sentence(including_word='term2')),
            self.setup_bookmark(website_title=random_sentence(including_word='term1'),
                                title=random_sentence(including_word='term2')),
            self.setup_bookmark(website_description=random_sentence(including_word='term1'),
                                title=random_sentence(including_word='term2')),
        ]
        self.tag1_bookmarks = [
            self.setup_bookmark(tags=[tag1]),
            self.setup_bookmark(title=random_sentence(), tags=[tag1]),
            self.setup_bookmark(description=random_sentence(), tags=[tag1]),
            self.setup_bookmark(website_title=random_sentence(), tags=[tag1]),
            self.setup_bookmark(website_description=random_sentence(), tags=[tag1]),
        ]
        self.term1_tag1_bookmarks = [
            self.setup_bookmark(url='http://example.com/term1', tags=[tag1]),
            self.setup_bookmark(title=random_sentence(including_word='term1'), tags=[tag1]),
            self.setup_bookmark(description=random_sentence(including_word='term1'), tags=[tag1]),
            self.setup_bookmark(website_title=random_sentence(including_word='term1'), tags=[tag1]),
            self.setup_bookmark(website_description=random_sentence(including_word='term1'), tags=[tag1]),
        ]
        self.tag2_bookmarks = [
            self.setup_bookmark(tags=[tag2]),
        ]
        self.tag1_tag2_bookmarks = [
            self.setup_bookmark(tags=[tag1, tag2]),
        ]

    def setup_tag_search_data(self):
        tag1 = self.setup_tag(name='tag1')
        tag2 = self.setup_tag(name='tag2')
        self.setup_tag(name='unused_tag1')

        self.other_bookmarks = [
            self.setup_bookmark(tags=[self.setup_tag()]),
            self.setup_bookmark(tags=[self.setup_tag()]),
            self.setup_bookmark(tags=[self.setup_tag()]),
        ]
        self.term1_bookmarks = [
            self.setup_bookmark(url='http://example.com/term1', tags=[self.setup_tag()]),
            self.setup_bookmark(title=random_sentence(including_word='term1'), tags=[self.setup_tag()]),
            self.setup_bookmark(description=random_sentence(including_word='term1'), tags=[self.setup_tag()]),
            self.setup_bookmark(website_title=random_sentence(including_word='term1'), tags=[self.setup_tag()]),
            self.setup_bookmark(website_description=random_sentence(including_word='term1'), tags=[self.setup_tag()]),
        ]
        self.term1_term2_bookmarks = [
            self.setup_bookmark(url='http://example.com/term1/term2', tags=[self.setup_tag()]),
            self.setup_bookmark(title=random_sentence(including_word='term1'),
                                description=random_sentence(including_word='term2'),
                                tags=[self.setup_tag()]),
            self.setup_bookmark(description=random_sentence(including_word='term1'),
                                title=random_sentence(including_word='term2'),
                                tags=[self.setup_tag()]),
            self.setup_bookmark(website_title=random_sentence(including_word='term1'),
                                title=random_sentence(including_word='term2'),
                                tags=[self.setup_tag()]),
            self.setup_bookmark(website_description=random_sentence(including_word='term1'),
                                title=random_sentence(including_word='term2'),
                                tags=[self.setup_tag()]),
        ]
        self.tag1_bookmarks = [
            self.setup_bookmark(tags=[tag1, self.setup_tag()]),
            self.setup_bookmark(title=random_sentence(), tags=[tag1, self.setup_tag()]),
            self.setup_bookmark(description=random_sentence(), tags=[tag1, self.setup_tag()]),
            self.setup_bookmark(website_title=random_sentence(), tags=[tag1, self.setup_tag()]),
            self.setup_bookmark(website_description=random_sentence(), tags=[tag1, self.setup_tag()]),
        ]
        self.term1_tag1_bookmarks = [
            self.setup_bookmark(url='http://example.com/term1', tags=[tag1, self.setup_tag()]),
            self.setup_bookmark(title=random_sentence(including_word='term1'), tags=[tag1, self.setup_tag()]),
            self.setup_bookmark(description=random_sentence(including_word='term1'), tags=[tag1, self.setup_tag()]),
            self.setup_bookmark(website_title=random_sentence(including_word='term1'), tags=[tag1, self.setup_tag()]),
            self.setup_bookmark(website_description=random_sentence(including_word='term1'),
                                tags=[tag1, self.setup_tag()]),
        ]
        self.tag2_bookmarks = [
            self.setup_bookmark(tags=[tag2, self.setup_tag()]),
        ]
        self.tag1_tag2_bookmarks = [
            self.setup_bookmark(tags=[tag1, tag2, self.setup_tag()]),
        ]

    def get_tags_from_bookmarks(self, bookmarks: [Bookmark]):
        all_tags = []
        for bookmark in bookmarks:
            all_tags = all_tags + list(bookmark.tags.all())
        return all_tags

    def assertQueryResult(self, query: QuerySet, item_lists: [[any]]):
        expected_items = []
        for item_list in item_lists:
            expected_items = expected_items + item_list

        expected_items = unique(expected_items, operator.attrgetter('id'))

        self.assertCountEqual(list(query), expected_items)

    def test_query_bookmarks_should_return_all_for_empty_query(self):
        self.setup_bookmark_search_data()

        query = queries.query_bookmarks(self.get_or_create_test_user(), '')
        self.assertQueryResult(query, [
            self.other_bookmarks,
            self.term1_bookmarks,
            self.term1_term2_bookmarks,
            self.tag1_bookmarks,
            self.term1_tag1_bookmarks,
            self.tag2_bookmarks,
            self.tag1_tag2_bookmarks
        ])

    def test_query_bookmarks_should_search_single_term(self):
        self.setup_bookmark_search_data()

        query = queries.query_bookmarks(self.get_or_create_test_user(), 'term1')
        self.assertQueryResult(query, [
            self.term1_bookmarks,
            self.term1_term2_bookmarks,
            self.term1_tag1_bookmarks
        ])

    def test_query_bookmarks_should_search_multiple_terms(self):
        self.setup_bookmark_search_data()

        query = queries.query_bookmarks(self.get_or_create_test_user(), 'term2 term1')

        self.assertQueryResult(query, [self.term1_term2_bookmarks])

    def test_query_bookmarks_should_search_single_tag(self):
        self.setup_bookmark_search_data()

        query = queries.query_bookmarks(self.get_or_create_test_user(), '#tag1')

        self.assertQueryResult(query, [self.tag1_bookmarks, self.tag1_tag2_bookmarks, self.term1_tag1_bookmarks])

    def test_query_bookmarks_should_search_multiple_tags(self):
        self.setup_bookmark_search_data()

        query = queries.query_bookmarks(self.get_or_create_test_user(), '#tag1 #tag2')

        self.assertQueryResult(query, [self.tag1_tag2_bookmarks])

    def test_query_bookmarks_should_search_multiple_tags_ignoring_casing(self):
        self.setup_bookmark_search_data()

        query = queries.query_bookmarks(self.get_or_create_test_user(), '#Tag1 #TAG2')

        self.assertQueryResult(query, [self.tag1_tag2_bookmarks])

    def test_query_bookmarks_should_search_terms_and_tags_combined(self):
        self.setup_bookmark_search_data()

        query = queries.query_bookmarks(self.get_or_create_test_user(), 'term1 #tag1')

        self.assertQueryResult(query, [self.term1_tag1_bookmarks])

    def test_query_bookmarks_should_return_no_matches(self):
        self.setup_bookmark_search_data()

        query = queries.query_bookmarks(self.get_or_create_test_user(), 'term3')
        self.assertQueryResult(query, [])

        query = queries.query_bookmarks(self.get_or_create_test_user(), 'term1 term3')
        self.assertQueryResult(query, [])

        query = queries.query_bookmarks(self.get_or_create_test_user(), 'term1 #tag2')
        self.assertQueryResult(query, [])

        query = queries.query_bookmarks(self.get_or_create_test_user(), '#tag3')
        self.assertQueryResult(query, [])

        # Unused tag
        query = queries.query_bookmarks(self.get_or_create_test_user(), '#unused_tag1')
        self.assertQueryResult(query, [])

        # Unused tag combined with tag that is used
        query = queries.query_bookmarks(self.get_or_create_test_user(), '#tag1 #unused_tag1')
        self.assertQueryResult(query, [])

        # Unused tag combined with term that is used
        query = queries.query_bookmarks(self.get_or_create_test_user(), 'term1 #unused_tag1')
        self.assertQueryResult(query, [])

    def test_query_bookmarks_should_not_return_archived_bookmarks(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        self.setup_bookmark(is_archived=True)
        self.setup_bookmark(is_archived=True)
        self.setup_bookmark(is_archived=True)

        query = queries.query_bookmarks(self.get_or_create_test_user(), '')

        self.assertQueryResult(query, [[bookmark1, bookmark2]])

    def test_query_archived_bookmarks_should_not_return_unarchived_bookmarks(self):
        bookmark1 = self.setup_bookmark(is_archived=True)
        bookmark2 = self.setup_bookmark(is_archived=True)
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()

        query = queries.query_archived_bookmarks(self.get_or_create_test_user(), '')

        self.assertQueryResult(query, [[bookmark1, bookmark2]])

    def test_query_bookmarks_should_only_return_user_owned_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        owned_bookmarks = [
            self.setup_bookmark(),
            self.setup_bookmark(),
            self.setup_bookmark(),
        ]
        self.setup_bookmark(user=other_user)
        self.setup_bookmark(user=other_user)
        self.setup_bookmark(user=other_user)

        query = queries.query_bookmarks(self.user, '')

        self.assertQueryResult(query, [owned_bookmarks])

    def test_query_archived_bookmarks_should_only_return_user_owned_bookmarks(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        owned_bookmarks = [
            self.setup_bookmark(is_archived=True),
            self.setup_bookmark(is_archived=True),
            self.setup_bookmark(is_archived=True),
        ]
        self.setup_bookmark(is_archived=True, user=other_user)
        self.setup_bookmark(is_archived=True, user=other_user)
        self.setup_bookmark(is_archived=True, user=other_user)

        query = queries.query_archived_bookmarks(self.user, '')

        self.assertQueryResult(query, [owned_bookmarks])

    def test_query_bookmarks_should_use_tag_projection(self):
        self.setup_bookmark_search_data()

        # Test projection on bookmarks with tags
        query = queries.query_bookmarks(self.user, '#tag1 #tag2')

        for bookmark in query:
            self.assertEqual(bookmark.tag_count, 2)
            self.assertEqual(bookmark.tag_string, 'tag1,tag2')
            self.assertTrue(bookmark.tag_projection)

        # Test projection on bookmarks without tags
        query = queries.query_bookmarks(self.user, 'term2')

        for bookmark in query:
            self.assertEqual(bookmark.tag_count, 0)
            self.assertEqual(bookmark.tag_string, None)
            self.assertTrue(bookmark.tag_projection)

    def test_query_bookmarks_untagged_should_return_untagged_bookmarks_only(self):
        tag = self.setup_tag()
        untagged_bookmark = self.setup_bookmark()
        self.setup_bookmark(tags=[tag])
        self.setup_bookmark(tags=[tag])

        query = queries.query_bookmarks(self.user, '!untagged')
        self.assertCountEqual(list(query), [untagged_bookmark])

    def test_query_bookmarks_untagged_should_be_combinable_with_search_terms(self):
        tag = self.setup_tag()
        untagged_bookmark = self.setup_bookmark(title='term1')
        self.setup_bookmark(title='term2')
        self.setup_bookmark(tags=[tag])

        query = queries.query_bookmarks(self.user, '!untagged term1')
        self.assertCountEqual(list(query), [untagged_bookmark])

    def test_query_bookmarks_untagged_should_not_be_combinable_with_tags(self):
        tag = self.setup_tag()
        self.setup_bookmark()
        self.setup_bookmark(tags=[tag])
        self.setup_bookmark(tags=[tag])

        query = queries.query_bookmarks(self.user, f'!untagged #{tag.name}')
        self.assertCountEqual(list(query), [])

    def test_query_archived_bookmarks_untagged_should_return_untagged_bookmarks_only(self):
        tag = self.setup_tag()
        untagged_bookmark = self.setup_bookmark(is_archived=True)
        self.setup_bookmark(is_archived=True, tags=[tag])
        self.setup_bookmark(is_archived=True, tags=[tag])

        query = queries.query_archived_bookmarks(self.user, '!untagged')
        self.assertCountEqual(list(query), [untagged_bookmark])

    def test_query_archived_bookmarks_untagged_should_be_combinable_with_search_terms(self):
        tag = self.setup_tag()
        untagged_bookmark = self.setup_bookmark(is_archived=True, title='term1')
        self.setup_bookmark(is_archived=True, title='term2')
        self.setup_bookmark(is_archived=True, tags=[tag])

        query = queries.query_archived_bookmarks(self.user, '!untagged term1')
        self.assertCountEqual(list(query), [untagged_bookmark])

    def test_query_archived_bookmarks_untagged_should_not_be_combinable_with_tags(self):
        tag = self.setup_tag()
        self.setup_bookmark(is_archived=True)
        self.setup_bookmark(is_archived=True, tags=[tag])
        self.setup_bookmark(is_archived=True, tags=[tag])

        query = queries.query_archived_bookmarks(self.user, f'!untagged #{tag.name}')
        self.assertCountEqual(list(query), [])

    def test_query_bookmark_tags_should_return_all_tags_for_empty_query(self):
        self.setup_tag_search_data()

        query = queries.query_bookmark_tags(self.user, '')

        self.assertQueryResult(query, [
            self.get_tags_from_bookmarks(self.other_bookmarks),
            self.get_tags_from_bookmarks(self.term1_bookmarks),
            self.get_tags_from_bookmarks(self.term1_term2_bookmarks),
            self.get_tags_from_bookmarks(self.tag1_bookmarks),
            self.get_tags_from_bookmarks(self.term1_tag1_bookmarks),
            self.get_tags_from_bookmarks(self.tag2_bookmarks),
            self.get_tags_from_bookmarks(self.tag1_tag2_bookmarks),
        ])

    def test_query_bookmark_tags_should_search_single_term(self):
        self.setup_tag_search_data()

        query = queries.query_bookmark_tags(self.user, 'term1')

        self.assertQueryResult(query, [
            self.get_tags_from_bookmarks(self.term1_bookmarks),
            self.get_tags_from_bookmarks(self.term1_term2_bookmarks),
            self.get_tags_from_bookmarks(self.term1_tag1_bookmarks),
        ])

    def test_query_bookmark_tags_should_search_multiple_terms(self):
        self.setup_tag_search_data()

        query = queries.query_bookmark_tags(self.user, 'term2 term1')

        self.assertQueryResult(query, [
            self.get_tags_from_bookmarks(self.term1_term2_bookmarks),
        ])

    def test_query_bookmark_tags_should_search_single_tag(self):
        self.setup_tag_search_data()

        query = queries.query_bookmark_tags(self.user, '#tag1')

        self.assertQueryResult(query, [
            self.get_tags_from_bookmarks(self.tag1_bookmarks),
            self.get_tags_from_bookmarks(self.term1_tag1_bookmarks),
            self.get_tags_from_bookmarks(self.tag1_tag2_bookmarks),
        ])

    def test_query_bookmark_tags_should_search_multiple_tags(self):
        self.setup_tag_search_data()

        query = queries.query_bookmark_tags(self.user, '#tag1 #tag2')

        self.assertQueryResult(query, [
            self.get_tags_from_bookmarks(self.tag1_tag2_bookmarks),
        ])

    def test_query_bookmark_tags_should_search_multiple_tags_ignoring_casing(self):
        self.setup_tag_search_data()

        query = queries.query_bookmark_tags(self.user, '#Tag1 #TAG2')

        self.assertQueryResult(query, [
            self.get_tags_from_bookmarks(self.tag1_tag2_bookmarks),
        ])

    def test_query_bookmark_tags_should_search_term_and_tag_combined(self):
        self.setup_tag_search_data()

        query = queries.query_bookmark_tags(self.user, 'term1 #tag1')

        self.assertQueryResult(query, [
            self.get_tags_from_bookmarks(self.term1_tag1_bookmarks),
        ])

    def test_query_bookmark_tags_should_return_no_matches(self):
        self.setup_tag_search_data()

        query = queries.query_bookmark_tags(self.get_or_create_test_user(), 'term3')
        self.assertQueryResult(query, [])

        query = queries.query_bookmark_tags(self.get_or_create_test_user(), 'term1 term3')
        self.assertQueryResult(query, [])

        query = queries.query_bookmark_tags(self.get_or_create_test_user(), 'term1 #tag2')
        self.assertQueryResult(query, [])

        query = queries.query_bookmark_tags(self.get_or_create_test_user(), '#tag3')
        self.assertQueryResult(query, [])

        # Unused tag
        query = queries.query_bookmark_tags(self.get_or_create_test_user(), '#unused_tag1')
        self.assertQueryResult(query, [])

        # Unused tag combined with tag that is used
        query = queries.query_bookmark_tags(self.get_or_create_test_user(), '#tag1 #unused_tag1')
        self.assertQueryResult(query, [])

        # Unused tag combined with term that is used
        query = queries.query_bookmark_tags(self.get_or_create_test_user(), 'term1 #unused_tag1')
        self.assertQueryResult(query, [])

    def test_query_bookmark_tags_should_return_tags_for_unarchived_bookmarks_only(self):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        self.setup_bookmark(tags=[tag1])
        self.setup_bookmark()
        self.setup_bookmark(is_archived=True, tags=[tag2])

        query = queries.query_bookmark_tags(self.get_or_create_test_user(), '')

        self.assertQueryResult(query, [[tag1]])

    def test_query_bookmark_tags_should_return_distinct_tags(self):
        tag = self.setup_tag()
        self.setup_bookmark(tags=[tag])
        self.setup_bookmark(tags=[tag])
        self.setup_bookmark(tags=[tag])

        query = queries.query_bookmark_tags(self.get_or_create_test_user(), '')

        self.assertQueryResult(query, [[tag]])

    def test_query_archived_bookmark_tags_should_return_tags_for_archived_bookmarks_only(self):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        self.setup_bookmark(tags=[tag1])
        self.setup_bookmark()
        self.setup_bookmark(is_archived=True, tags=[tag2])

        query = queries.query_archived_bookmark_tags(self.get_or_create_test_user(), '')

        self.assertQueryResult(query, [[tag2]])

    def test_query_archived_bookmark_tags_should_return_distinct_tags(self):
        tag = self.setup_tag()
        self.setup_bookmark(is_archived=True, tags=[tag])
        self.setup_bookmark(is_archived=True, tags=[tag])
        self.setup_bookmark(is_archived=True, tags=[tag])

        query = queries.query_archived_bookmark_tags(self.get_or_create_test_user(), '')

        self.assertQueryResult(query, [[tag]])

    def test_query_bookmark_tags_should_only_return_user_owned_tags(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        owned_bookmarks = [
            self.setup_bookmark(tags=[self.setup_tag()]),
            self.setup_bookmark(tags=[self.setup_tag()]),
            self.setup_bookmark(tags=[self.setup_tag()]),
        ]
        self.setup_bookmark(user=other_user, tags=[self.setup_tag(user=other_user)])
        self.setup_bookmark(user=other_user, tags=[self.setup_tag(user=other_user)])
        self.setup_bookmark(user=other_user, tags=[self.setup_tag(user=other_user)])

        query = queries.query_bookmark_tags(self.user, '')

        self.assertQueryResult(query, [self.get_tags_from_bookmarks(owned_bookmarks)])

    def test_query_archived_bookmark_tags_should_only_return_user_owned_tags(self):
        other_user = User.objects.create_user('otheruser', 'otheruser@example.com', 'password123')
        owned_bookmarks = [
            self.setup_bookmark(is_archived=True, tags=[self.setup_tag()]),
            self.setup_bookmark(is_archived=True, tags=[self.setup_tag()]),
            self.setup_bookmark(is_archived=True, tags=[self.setup_tag()]),
        ]
        self.setup_bookmark(is_archived=True, user=other_user, tags=[self.setup_tag(user=other_user)])
        self.setup_bookmark(is_archived=True, user=other_user, tags=[self.setup_tag(user=other_user)])
        self.setup_bookmark(is_archived=True, user=other_user, tags=[self.setup_tag(user=other_user)])

        query = queries.query_archived_bookmark_tags(self.user, '')

        self.assertQueryResult(query, [self.get_tags_from_bookmarks(owned_bookmarks)])

    def test_query_bookmark_tags_untagged_should_never_return_any_tags(self):
        tag = self.setup_tag()
        self.setup_bookmark()
        self.setup_bookmark(title='term1')
        self.setup_bookmark(title='term1', tags=[tag])
        self.setup_bookmark(tags=[tag])

        query = queries.query_bookmark_tags(self.user, '!untagged')
        self.assertCountEqual(list(query), [])

        query = queries.query_bookmark_tags(self.user, '!untagged term1')
        self.assertCountEqual(list(query), [])

        query = queries.query_bookmark_tags(self.user, f'!untagged #{tag.name}')
        self.assertCountEqual(list(query), [])

    def test_query_archived_bookmark_tags_untagged_should_never_return_any_tags(self):
        tag = self.setup_tag()
        self.setup_bookmark(is_archived=True)
        self.setup_bookmark(is_archived=True, title='term1')
        self.setup_bookmark(is_archived=True, title='term1', tags=[tag])
        self.setup_bookmark(is_archived=True, tags=[tag])

        query = queries.query_archived_bookmark_tags(self.user, '!untagged')
        self.assertCountEqual(list(query), [])

        query = queries.query_archived_bookmark_tags(self.user, '!untagged term1')
        self.assertCountEqual(list(query), [])

        query = queries.query_archived_bookmark_tags(self.user, f'!untagged #{tag.name}')
        self.assertCountEqual(list(query), [])
