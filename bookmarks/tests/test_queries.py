import operator
import datetime

from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.test import TestCase
from django.utils import timezone

from bookmarks import queries
from bookmarks.models import BookmarkSearch, UserProfile
from bookmarks.tests.helpers import BookmarkFactoryMixin, random_sentence
from bookmarks.utils import unique

User = get_user_model()


class QueriesTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self):
        self.profile = self.get_or_create_test_user().profile

    def setup_bookmark_search_data(self) -> None:
        tag1 = self.setup_tag(name="tag1")
        tag2 = self.setup_tag(name="tag2")
        self.setup_tag(name="unused_tag1")

        self.other_bookmarks = [
            self.setup_bookmark(),
            self.setup_bookmark(),
            self.setup_bookmark(),
        ]
        self.term1_bookmarks = [
            self.setup_bookmark(url="http://example.com/term1"),
            self.setup_bookmark(title=random_sentence(including_word="term1")),
            self.setup_bookmark(title=random_sentence(including_word="TERM1")),
            self.setup_bookmark(description=random_sentence(including_word="term1")),
            self.setup_bookmark(description=random_sentence(including_word="TERM1")),
            self.setup_bookmark(notes=random_sentence(including_word="term1")),
            self.setup_bookmark(notes=random_sentence(including_word="TERM1")),
            self.setup_bookmark(website_title=random_sentence(including_word="term1")),
            self.setup_bookmark(website_title=random_sentence(including_word="TERM1")),
            self.setup_bookmark(
                website_description=random_sentence(including_word="term1")
            ),
            self.setup_bookmark(
                website_description=random_sentence(including_word="TERM1")
            ),
        ]
        self.term1_term2_bookmarks = [
            self.setup_bookmark(url="http://example.com/term1/term2"),
            self.setup_bookmark(
                title=random_sentence(including_word="term1"),
                description=random_sentence(including_word="term2"),
            ),
            self.setup_bookmark(
                description=random_sentence(including_word="term1"),
                title=random_sentence(including_word="term2"),
            ),
            self.setup_bookmark(
                website_title=random_sentence(including_word="term1"),
                title=random_sentence(including_word="term2"),
            ),
            self.setup_bookmark(
                website_description=random_sentence(including_word="term1"),
                title=random_sentence(including_word="term2"),
            ),
        ]
        self.tag1_bookmarks = [
            self.setup_bookmark(tags=[tag1]),
            self.setup_bookmark(title=random_sentence(), tags=[tag1]),
            self.setup_bookmark(description=random_sentence(), tags=[tag1]),
            self.setup_bookmark(website_title=random_sentence(), tags=[tag1]),
            self.setup_bookmark(website_description=random_sentence(), tags=[tag1]),
        ]
        self.tag1_as_term_bookmarks = [
            self.setup_bookmark(url="http://example.com/tag1"),
            self.setup_bookmark(title=random_sentence(including_word="tag1")),
            self.setup_bookmark(description=random_sentence(including_word="tag1")),
            self.setup_bookmark(website_title=random_sentence(including_word="tag1")),
            self.setup_bookmark(
                website_description=random_sentence(including_word="tag1")
            ),
        ]
        self.term1_tag1_bookmarks = [
            self.setup_bookmark(url="http://example.com/term1", tags=[tag1]),
            self.setup_bookmark(
                title=random_sentence(including_word="term1"), tags=[tag1]
            ),
            self.setup_bookmark(
                description=random_sentence(including_word="term1"), tags=[tag1]
            ),
            self.setup_bookmark(
                website_title=random_sentence(including_word="term1"), tags=[tag1]
            ),
            self.setup_bookmark(
                website_description=random_sentence(including_word="term1"), tags=[tag1]
            ),
        ]
        self.tag2_bookmarks = [
            self.setup_bookmark(tags=[tag2]),
        ]
        self.tag1_tag2_bookmarks = [
            self.setup_bookmark(tags=[tag1, tag2]),
        ]

    def setup_tag_search_data(self):
        tag1 = self.setup_tag(name="tag1")
        tag2 = self.setup_tag(name="tag2")
        self.setup_tag(name="unused_tag1")

        self.other_bookmarks = [
            self.setup_bookmark(tags=[self.setup_tag()]),
            self.setup_bookmark(tags=[self.setup_tag()]),
            self.setup_bookmark(tags=[self.setup_tag()]),
        ]
        self.term1_bookmarks = [
            self.setup_bookmark(
                url="http://example.com/term1", tags=[self.setup_tag()]
            ),
            self.setup_bookmark(
                title=random_sentence(including_word="term1"), tags=[self.setup_tag()]
            ),
            self.setup_bookmark(
                title=random_sentence(including_word="TERM1"), tags=[self.setup_tag()]
            ),
            self.setup_bookmark(
                description=random_sentence(including_word="term1"),
                tags=[self.setup_tag()],
            ),
            self.setup_bookmark(
                description=random_sentence(including_word="TERM1"),
                tags=[self.setup_tag()],
            ),
            self.setup_bookmark(
                notes=random_sentence(including_word="term1"), tags=[self.setup_tag()]
            ),
            self.setup_bookmark(
                notes=random_sentence(including_word="TERM1"), tags=[self.setup_tag()]
            ),
            self.setup_bookmark(
                website_title=random_sentence(including_word="term1"),
                tags=[self.setup_tag()],
            ),
            self.setup_bookmark(
                website_title=random_sentence(including_word="TERM1"),
                tags=[self.setup_tag()],
            ),
            self.setup_bookmark(
                website_description=random_sentence(including_word="term1"),
                tags=[self.setup_tag()],
            ),
            self.setup_bookmark(
                website_description=random_sentence(including_word="TERM1"),
                tags=[self.setup_tag()],
            ),
        ]
        self.term1_term2_bookmarks = [
            self.setup_bookmark(
                url="http://example.com/term1/term2", tags=[self.setup_tag()]
            ),
            self.setup_bookmark(
                title=random_sentence(including_word="term1"),
                description=random_sentence(including_word="term2"),
                tags=[self.setup_tag()],
            ),
            self.setup_bookmark(
                description=random_sentence(including_word="term1"),
                title=random_sentence(including_word="term2"),
                tags=[self.setup_tag()],
            ),
            self.setup_bookmark(
                website_title=random_sentence(including_word="term1"),
                title=random_sentence(including_word="term2"),
                tags=[self.setup_tag()],
            ),
            self.setup_bookmark(
                website_description=random_sentence(including_word="term1"),
                title=random_sentence(including_word="term2"),
                tags=[self.setup_tag()],
            ),
        ]
        self.tag1_bookmarks = [
            self.setup_bookmark(tags=[tag1, self.setup_tag()]),
            self.setup_bookmark(title=random_sentence(), tags=[tag1, self.setup_tag()]),
            self.setup_bookmark(
                description=random_sentence(), tags=[tag1, self.setup_tag()]
            ),
            self.setup_bookmark(
                website_title=random_sentence(), tags=[tag1, self.setup_tag()]
            ),
            self.setup_bookmark(
                website_description=random_sentence(), tags=[tag1, self.setup_tag()]
            ),
        ]
        self.tag1_as_term_bookmarks = [
            self.setup_bookmark(url="http://example.com/tag1"),
            self.setup_bookmark(title=random_sentence(including_word="tag1")),
            self.setup_bookmark(description=random_sentence(including_word="tag1")),
            self.setup_bookmark(website_title=random_sentence(including_word="tag1")),
            self.setup_bookmark(
                website_description=random_sentence(including_word="tag1")
            ),
        ]
        self.term1_tag1_bookmarks = [
            self.setup_bookmark(
                url="http://example.com/term1", tags=[tag1, self.setup_tag()]
            ),
            self.setup_bookmark(
                title=random_sentence(including_word="term1"),
                tags=[tag1, self.setup_tag()],
            ),
            self.setup_bookmark(
                description=random_sentence(including_word="term1"),
                tags=[tag1, self.setup_tag()],
            ),
            self.setup_bookmark(
                website_title=random_sentence(including_word="term1"),
                tags=[tag1, self.setup_tag()],
            ),
            self.setup_bookmark(
                website_description=random_sentence(including_word="term1"),
                tags=[tag1, self.setup_tag()],
            ),
        ]
        self.tag2_bookmarks = [
            self.setup_bookmark(tags=[tag2, self.setup_tag()]),
        ]
        self.tag1_tag2_bookmarks = [
            self.setup_bookmark(tags=[tag1, tag2, self.setup_tag()]),
        ]

    def assertQueryResult(self, query: QuerySet, item_lists: [[any]]):
        expected_items = []
        for item_list in item_lists:
            expected_items = expected_items + item_list

        expected_items = unique(expected_items, operator.attrgetter("id"))

        self.assertCountEqual(list(query), expected_items)

    def test_query_bookmarks_should_return_all_for_empty_query(self):
        self.setup_bookmark_search_data()

        query = queries.query_bookmarks(self.user, self.profile, BookmarkSearch(q=""))
        self.assertQueryResult(
            query,
            [
                self.other_bookmarks,
                self.term1_bookmarks,
                self.term1_term2_bookmarks,
                self.tag1_bookmarks,
                self.tag1_as_term_bookmarks,
                self.term1_tag1_bookmarks,
                self.tag2_bookmarks,
                self.tag1_tag2_bookmarks,
            ],
        )

    def test_query_bookmarks_should_search_single_term(self):
        self.setup_bookmark_search_data()

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="term1")
        )
        self.assertQueryResult(
            query,
            [
                self.term1_bookmarks,
                self.term1_term2_bookmarks,
                self.term1_tag1_bookmarks,
            ],
        )

    def test_query_bookmarks_should_search_multiple_terms(self):
        self.setup_bookmark_search_data()

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="term2 term1")
        )

        self.assertQueryResult(query, [self.term1_term2_bookmarks])

    def test_query_bookmarks_should_search_single_tag(self):
        self.setup_bookmark_search_data()

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="#tag1")
        )

        self.assertQueryResult(
            query,
            [self.tag1_bookmarks, self.tag1_tag2_bookmarks, self.term1_tag1_bookmarks],
        )

    def test_query_bookmarks_should_search_multiple_tags(self):
        self.setup_bookmark_search_data()

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="#tag1 #tag2")
        )

        self.assertQueryResult(query, [self.tag1_tag2_bookmarks])

    def test_query_bookmarks_should_search_multiple_tags_ignoring_casing(self):
        self.setup_bookmark_search_data()

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="#Tag1 #TAG2")
        )

        self.assertQueryResult(query, [self.tag1_tag2_bookmarks])

    def test_query_bookmarks_should_search_terms_and_tags_combined(self):
        self.setup_bookmark_search_data()

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="term1 #tag1")
        )

        self.assertQueryResult(query, [self.term1_tag1_bookmarks])

    def test_query_bookmarks_in_strict_mode_should_not_search_tags_as_terms(self):
        self.setup_bookmark_search_data()

        self.profile.tag_search = UserProfile.TAG_SEARCH_STRICT
        self.profile.save()

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="tag1")
        )
        self.assertQueryResult(query, [self.tag1_as_term_bookmarks])

    def test_query_bookmarks_in_lax_mode_should_search_tags_as_terms(self):
        self.setup_bookmark_search_data()

        self.profile.tag_search = UserProfile.TAG_SEARCH_LAX
        self.profile.save()

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="tag1")
        )
        self.assertQueryResult(
            query,
            [
                self.tag1_bookmarks,
                self.tag1_as_term_bookmarks,
                self.tag1_tag2_bookmarks,
                self.term1_tag1_bookmarks,
            ],
        )

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="tag1 term1")
        )
        self.assertQueryResult(
            query,
            [
                self.term1_tag1_bookmarks,
            ],
        )

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="tag1 tag2")
        )
        self.assertQueryResult(
            query,
            [
                self.tag1_tag2_bookmarks,
            ],
        )

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="tag1 #tag2")
        )
        self.assertQueryResult(
            query,
            [
                self.tag1_tag2_bookmarks,
            ],
        )

    def test_query_bookmarks_should_return_no_matches(self):
        self.setup_bookmark_search_data()

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="term3")
        )
        self.assertQueryResult(query, [])

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="term1 term3")
        )
        self.assertQueryResult(query, [])

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="term1 #tag2")
        )
        self.assertQueryResult(query, [])

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="#tag3")
        )
        self.assertQueryResult(query, [])

        # Unused tag
        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="#unused_tag1")
        )
        self.assertQueryResult(query, [])

        # Unused tag combined with tag that is used
        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="#tag1 #unused_tag1")
        )
        self.assertQueryResult(query, [])

        # Unused tag combined with term that is used
        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="term1 #unused_tag1")
        )
        self.assertQueryResult(query, [])

    def test_query_bookmarks_should_not_return_archived_bookmarks(self):
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark()
        self.setup_bookmark(is_archived=True)
        self.setup_bookmark(is_archived=True)
        self.setup_bookmark(is_archived=True)

        query = queries.query_bookmarks(self.user, self.profile, BookmarkSearch(q=""))

        self.assertQueryResult(query, [[bookmark1, bookmark2]])

    def test_query_archived_bookmarks_should_not_return_unarchived_bookmarks(self):
        bookmark1 = self.setup_bookmark(is_archived=True)
        bookmark2 = self.setup_bookmark(is_archived=True)
        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()

        query = queries.query_archived_bookmarks(
            self.user, self.profile, BookmarkSearch(q="")
        )

        self.assertQueryResult(query, [[bookmark1, bookmark2]])

    def test_query_bookmarks_should_only_return_user_owned_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        owned_bookmarks = [
            self.setup_bookmark(),
            self.setup_bookmark(),
            self.setup_bookmark(),
        ]
        self.setup_bookmark(user=other_user)
        self.setup_bookmark(user=other_user)
        self.setup_bookmark(user=other_user)

        query = queries.query_bookmarks(self.user, self.profile, BookmarkSearch(q=""))

        self.assertQueryResult(query, [owned_bookmarks])

    def test_query_archived_bookmarks_should_only_return_user_owned_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        owned_bookmarks = [
            self.setup_bookmark(is_archived=True),
            self.setup_bookmark(is_archived=True),
            self.setup_bookmark(is_archived=True),
        ]
        self.setup_bookmark(is_archived=True, user=other_user)
        self.setup_bookmark(is_archived=True, user=other_user)
        self.setup_bookmark(is_archived=True, user=other_user)

        query = queries.query_archived_bookmarks(
            self.user, self.profile, BookmarkSearch(q="")
        )

        self.assertQueryResult(query, [owned_bookmarks])

    def test_query_bookmarks_untagged_should_return_untagged_bookmarks_only(self):
        tag = self.setup_tag()
        untagged_bookmark = self.setup_bookmark()
        self.setup_bookmark(tags=[tag])
        self.setup_bookmark(tags=[tag])

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="!untagged")
        )
        self.assertCountEqual(list(query), [untagged_bookmark])

    def test_query_bookmarks_untagged_should_be_combinable_with_search_terms(self):
        tag = self.setup_tag()
        untagged_bookmark = self.setup_bookmark(title="term1")
        self.setup_bookmark(title="term2")
        self.setup_bookmark(tags=[tag])

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="!untagged term1")
        )
        self.assertCountEqual(list(query), [untagged_bookmark])

    def test_query_bookmarks_untagged_should_not_be_combinable_with_tags(self):
        tag = self.setup_tag()
        self.setup_bookmark()
        self.setup_bookmark(tags=[tag])
        self.setup_bookmark(tags=[tag])

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q=f"!untagged #{tag.name}")
        )
        self.assertCountEqual(list(query), [])

    def test_query_archived_bookmarks_untagged_should_return_untagged_bookmarks_only(
        self,
    ):
        tag = self.setup_tag()
        untagged_bookmark = self.setup_bookmark(is_archived=True)
        self.setup_bookmark(is_archived=True, tags=[tag])
        self.setup_bookmark(is_archived=True, tags=[tag])

        query = queries.query_archived_bookmarks(
            self.user, self.profile, BookmarkSearch(q="!untagged")
        )
        self.assertCountEqual(list(query), [untagged_bookmark])

    def test_query_archived_bookmarks_untagged_should_be_combinable_with_search_terms(
        self,
    ):
        tag = self.setup_tag()
        untagged_bookmark = self.setup_bookmark(is_archived=True, title="term1")
        self.setup_bookmark(is_archived=True, title="term2")
        self.setup_bookmark(is_archived=True, tags=[tag])

        query = queries.query_archived_bookmarks(
            self.user, self.profile, BookmarkSearch(q="!untagged term1")
        )
        self.assertCountEqual(list(query), [untagged_bookmark])

    def test_query_archived_bookmarks_untagged_should_not_be_combinable_with_tags(self):
        tag = self.setup_tag()
        self.setup_bookmark(is_archived=True)
        self.setup_bookmark(is_archived=True, tags=[tag])
        self.setup_bookmark(is_archived=True, tags=[tag])

        query = queries.query_archived_bookmarks(
            self.user, self.profile, BookmarkSearch(q=f"!untagged #{tag.name}")
        )
        self.assertCountEqual(list(query), [])

    def test_query_bookmarks_unread_should_return_unread_bookmarks_only(self):
        unread_bookmarks = self.setup_numbered_bookmarks(5, unread=True)
        read_bookmarks = self.setup_numbered_bookmarks(5, unread=False)

        # Legacy query filter
        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="!unread")
        )
        self.assertCountEqual(list(query), unread_bookmarks)

        # Bookmark search filter - off
        query = queries.query_bookmarks(
            self.user,
            self.profile,
            BookmarkSearch(unread=BookmarkSearch.FILTER_UNREAD_OFF),
        )
        self.assertCountEqual(list(query), read_bookmarks + unread_bookmarks)

        # Bookmark search filter - yes
        query = queries.query_bookmarks(
            self.user,
            self.profile,
            BookmarkSearch(unread=BookmarkSearch.FILTER_UNREAD_YES),
        )
        self.assertCountEqual(list(query), unread_bookmarks)

        # Bookmark search filter - no
        query = queries.query_bookmarks(
            self.user,
            self.profile,
            BookmarkSearch(unread=BookmarkSearch.FILTER_UNREAD_NO),
        )
        self.assertCountEqual(list(query), read_bookmarks)

    def test_query_archived_bookmarks_unread_should_return_unread_bookmarks_only(self):
        unread_bookmarks = self.setup_numbered_bookmarks(5, unread=True, archived=True)
        read_bookmarks = self.setup_numbered_bookmarks(5, unread=False, archived=True)

        # Legacy query filter
        query = queries.query_archived_bookmarks(
            self.user, self.profile, BookmarkSearch(q="!unread")
        )
        self.assertCountEqual(list(query), unread_bookmarks)

        # Bookmark search filter - off
        query = queries.query_archived_bookmarks(
            self.user,
            self.profile,
            BookmarkSearch(unread=BookmarkSearch.FILTER_UNREAD_OFF),
        )
        self.assertCountEqual(list(query), read_bookmarks + unread_bookmarks)

        # Bookmark search filter - yes
        query = queries.query_archived_bookmarks(
            self.user,
            self.profile,
            BookmarkSearch(unread=BookmarkSearch.FILTER_UNREAD_YES),
        )
        self.assertCountEqual(list(query), unread_bookmarks)

        # Bookmark search filter - no
        query = queries.query_archived_bookmarks(
            self.user,
            self.profile,
            BookmarkSearch(unread=BookmarkSearch.FILTER_UNREAD_NO),
        )
        self.assertCountEqual(list(query), read_bookmarks)

    def test_query_bookmarks_filter_shared(self):
        unshared_bookmarks = self.setup_numbered_bookmarks(5)
        shared_bookmarks = self.setup_numbered_bookmarks(5, shared=True)

        # Filter is off
        search = BookmarkSearch(shared=BookmarkSearch.FILTER_SHARED_OFF)
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), unshared_bookmarks + shared_bookmarks)

        # Filter for shared
        search = BookmarkSearch(shared=BookmarkSearch.FILTER_SHARED_SHARED)
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), shared_bookmarks)

        # Filter for unshared
        search = BookmarkSearch(shared=BookmarkSearch.FILTER_SHARED_UNSHARED)
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), unshared_bookmarks)

    def test_query_bookmark_tags_should_return_all_tags_for_empty_query(self):
        self.setup_tag_search_data()

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="")
        )

        self.assertQueryResult(
            query,
            [
                self.get_tags_from_bookmarks(self.other_bookmarks),
                self.get_tags_from_bookmarks(self.term1_bookmarks),
                self.get_tags_from_bookmarks(self.term1_term2_bookmarks),
                self.get_tags_from_bookmarks(self.tag1_bookmarks),
                self.get_tags_from_bookmarks(self.term1_tag1_bookmarks),
                self.get_tags_from_bookmarks(self.tag2_bookmarks),
                self.get_tags_from_bookmarks(self.tag1_tag2_bookmarks),
            ],
        )

    def test_query_bookmark_tags_should_search_single_term(self):
        self.setup_tag_search_data()

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="term1")
        )

        self.assertQueryResult(
            query,
            [
                self.get_tags_from_bookmarks(self.term1_bookmarks),
                self.get_tags_from_bookmarks(self.term1_term2_bookmarks),
                self.get_tags_from_bookmarks(self.term1_tag1_bookmarks),
            ],
        )

    def test_query_bookmark_tags_should_search_multiple_terms(self):
        self.setup_tag_search_data()

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="term2 term1")
        )

        self.assertQueryResult(
            query,
            [
                self.get_tags_from_bookmarks(self.term1_term2_bookmarks),
            ],
        )

    def test_query_bookmark_tags_should_search_single_tag(self):
        self.setup_tag_search_data()

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="#tag1")
        )

        self.assertQueryResult(
            query,
            [
                self.get_tags_from_bookmarks(self.tag1_bookmarks),
                self.get_tags_from_bookmarks(self.term1_tag1_bookmarks),
                self.get_tags_from_bookmarks(self.tag1_tag2_bookmarks),
            ],
        )

    def test_query_bookmark_tags_should_search_multiple_tags(self):
        self.setup_tag_search_data()

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="#tag1 #tag2")
        )

        self.assertQueryResult(
            query,
            [
                self.get_tags_from_bookmarks(self.tag1_tag2_bookmarks),
            ],
        )

    def test_query_bookmark_tags_should_search_multiple_tags_ignoring_casing(self):
        self.setup_tag_search_data()

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="#Tag1 #TAG2")
        )

        self.assertQueryResult(
            query,
            [
                self.get_tags_from_bookmarks(self.tag1_tag2_bookmarks),
            ],
        )

    def test_query_bookmark_tags_should_search_term_and_tag_combined(self):
        self.setup_tag_search_data()

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="term1 #tag1")
        )

        self.assertQueryResult(
            query,
            [
                self.get_tags_from_bookmarks(self.term1_tag1_bookmarks),
            ],
        )

    def test_query_bookmark_tags_in_strict_mode_should_not_search_tags_as_terms(self):
        self.setup_tag_search_data()

        self.profile.tag_search = UserProfile.TAG_SEARCH_STRICT
        self.profile.save()

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="tag1")
        )
        self.assertQueryResult(
            query, self.get_tags_from_bookmarks(self.tag1_as_term_bookmarks)
        )

    def test_query_bookmark_tags_in_lax_mode_should_search_tags_as_terms(self):
        self.setup_tag_search_data()

        self.profile.tag_search = UserProfile.TAG_SEARCH_LAX
        self.profile.save()

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="tag1")
        )
        self.assertQueryResult(
            query,
            [
                self.get_tags_from_bookmarks(self.tag1_bookmarks),
                self.get_tags_from_bookmarks(self.tag1_as_term_bookmarks),
                self.get_tags_from_bookmarks(self.tag1_tag2_bookmarks),
                self.get_tags_from_bookmarks(self.term1_tag1_bookmarks),
            ],
        )

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="tag1 term1")
        )
        self.assertQueryResult(
            query,
            [
                self.get_tags_from_bookmarks(self.term1_tag1_bookmarks),
            ],
        )

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="tag1 tag2")
        )
        self.assertQueryResult(
            query,
            [
                self.get_tags_from_bookmarks(self.tag1_tag2_bookmarks),
            ],
        )

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="tag1 #tag2")
        )
        self.assertQueryResult(
            query,
            [
                self.get_tags_from_bookmarks(self.tag1_tag2_bookmarks),
            ],
        )

    def test_query_bookmark_tags_should_return_no_matches(self):
        self.setup_tag_search_data()

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="term3")
        )
        self.assertQueryResult(query, [])

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="term1 term3")
        )
        self.assertQueryResult(query, [])

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="term1 #tag2")
        )
        self.assertQueryResult(query, [])

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="#tag3")
        )
        self.assertQueryResult(query, [])

        # Unused tag
        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="#unused_tag1")
        )
        self.assertQueryResult(query, [])

        # Unused tag combined with tag that is used
        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="#tag1 #unused_tag1")
        )
        self.assertQueryResult(query, [])

        # Unused tag combined with term that is used
        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="term1 #unused_tag1")
        )
        self.assertQueryResult(query, [])

    def test_query_bookmark_tags_should_return_tags_for_unarchived_bookmarks_only(self):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        self.setup_bookmark(tags=[tag1])
        self.setup_bookmark()
        self.setup_bookmark(is_archived=True, tags=[tag2])

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="")
        )

        self.assertQueryResult(query, [[tag1]])

    def test_query_bookmark_tags_should_return_distinct_tags(self):
        tag = self.setup_tag()
        self.setup_bookmark(tags=[tag])
        self.setup_bookmark(tags=[tag])
        self.setup_bookmark(tags=[tag])

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="")
        )

        self.assertQueryResult(query, [[tag]])

    def test_query_archived_bookmark_tags_should_return_tags_for_archived_bookmarks_only(
        self,
    ):
        tag1 = self.setup_tag()
        tag2 = self.setup_tag()
        self.setup_bookmark(tags=[tag1])
        self.setup_bookmark()
        self.setup_bookmark(is_archived=True, tags=[tag2])

        query = queries.query_archived_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="")
        )

        self.assertQueryResult(query, [[tag2]])

    def test_query_archived_bookmark_tags_should_return_distinct_tags(self):
        tag = self.setup_tag()
        self.setup_bookmark(is_archived=True, tags=[tag])
        self.setup_bookmark(is_archived=True, tags=[tag])
        self.setup_bookmark(is_archived=True, tags=[tag])

        query = queries.query_archived_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="")
        )

        self.assertQueryResult(query, [[tag]])

    def test_query_bookmark_tags_should_only_return_user_owned_tags(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        owned_bookmarks = [
            self.setup_bookmark(tags=[self.setup_tag()]),
            self.setup_bookmark(tags=[self.setup_tag()]),
            self.setup_bookmark(tags=[self.setup_tag()]),
        ]
        self.setup_bookmark(user=other_user, tags=[self.setup_tag(user=other_user)])
        self.setup_bookmark(user=other_user, tags=[self.setup_tag(user=other_user)])
        self.setup_bookmark(user=other_user, tags=[self.setup_tag(user=other_user)])

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="")
        )

        self.assertQueryResult(query, [self.get_tags_from_bookmarks(owned_bookmarks)])

    def test_query_archived_bookmark_tags_should_only_return_user_owned_tags(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        owned_bookmarks = [
            self.setup_bookmark(is_archived=True, tags=[self.setup_tag()]),
            self.setup_bookmark(is_archived=True, tags=[self.setup_tag()]),
            self.setup_bookmark(is_archived=True, tags=[self.setup_tag()]),
        ]
        self.setup_bookmark(
            is_archived=True, user=other_user, tags=[self.setup_tag(user=other_user)]
        )
        self.setup_bookmark(
            is_archived=True, user=other_user, tags=[self.setup_tag(user=other_user)]
        )
        self.setup_bookmark(
            is_archived=True, user=other_user, tags=[self.setup_tag(user=other_user)]
        )

        query = queries.query_archived_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="")
        )

        self.assertQueryResult(query, [self.get_tags_from_bookmarks(owned_bookmarks)])

    def test_query_bookmark_tags_untagged_should_never_return_any_tags(self):
        tag = self.setup_tag()
        self.setup_bookmark()
        self.setup_bookmark(title="term1")
        self.setup_bookmark(title="term1", tags=[tag])
        self.setup_bookmark(tags=[tag])

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="!untagged")
        )
        self.assertCountEqual(list(query), [])

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="!untagged term1")
        )
        self.assertCountEqual(list(query), [])

        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q=f"!untagged #{tag.name}")
        )
        self.assertCountEqual(list(query), [])

    def test_query_archived_bookmark_tags_untagged_should_never_return_any_tags(self):
        tag = self.setup_tag()
        self.setup_bookmark(is_archived=True)
        self.setup_bookmark(is_archived=True, title="term1")
        self.setup_bookmark(is_archived=True, title="term1", tags=[tag])
        self.setup_bookmark(is_archived=True, tags=[tag])

        query = queries.query_archived_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="!untagged")
        )
        self.assertCountEqual(list(query), [])

        query = queries.query_archived_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="!untagged term1")
        )
        self.assertCountEqual(list(query), [])

        query = queries.query_archived_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q=f"!untagged #{tag.name}")
        )
        self.assertCountEqual(list(query), [])

    def test_query_bookmark_tags_filter_unread(self):
        unread_bookmarks = self.setup_numbered_bookmarks(5, unread=True, with_tags=True)
        read_bookmarks = self.setup_numbered_bookmarks(5, unread=False, with_tags=True)
        unread_tags = self.get_tags_from_bookmarks(unread_bookmarks)
        read_tags = self.get_tags_from_bookmarks(read_bookmarks)

        # Legacy query filter
        query = queries.query_bookmark_tags(
            self.user, self.profile, BookmarkSearch(q="!unread")
        )
        self.assertCountEqual(list(query), unread_tags)

        # Bookmark search filter - off
        query = queries.query_bookmark_tags(
            self.user,
            self.profile,
            BookmarkSearch(unread=BookmarkSearch.FILTER_UNREAD_OFF),
        )
        self.assertCountEqual(list(query), read_tags + unread_tags)

        # Bookmark search filter - yes
        query = queries.query_bookmark_tags(
            self.user,
            self.profile,
            BookmarkSearch(unread=BookmarkSearch.FILTER_UNREAD_YES),
        )
        self.assertCountEqual(list(query), unread_tags)

        # Bookmark search filter - no
        query = queries.query_bookmark_tags(
            self.user,
            self.profile,
            BookmarkSearch(unread=BookmarkSearch.FILTER_UNREAD_NO),
        )
        self.assertCountEqual(list(query), read_tags)

    def test_query_bookmark_tags_filter_shared(self):
        unshared_bookmarks = self.setup_numbered_bookmarks(5, with_tags=True)
        shared_bookmarks = self.setup_numbered_bookmarks(5, with_tags=True, shared=True)

        unshared_tags = self.get_tags_from_bookmarks(unshared_bookmarks)
        shared_tags = self.get_tags_from_bookmarks(shared_bookmarks)
        all_tags = unshared_tags + shared_tags

        # Filter is off
        search = BookmarkSearch(shared=BookmarkSearch.FILTER_SHARED_OFF)
        query = queries.query_bookmark_tags(self.user, self.profile, search)
        self.assertCountEqual(list(query), all_tags)

        # Filter for shared
        search = BookmarkSearch(shared=BookmarkSearch.FILTER_SHARED_SHARED)
        query = queries.query_bookmark_tags(self.user, self.profile, search)
        self.assertCountEqual(list(query), shared_tags)

        # Filter for unshared
        search = BookmarkSearch(shared=BookmarkSearch.FILTER_SHARED_UNSHARED)
        query = queries.query_bookmark_tags(self.user, self.profile, search)
        self.assertCountEqual(list(query), unshared_tags)

    def test_query_shared_bookmarks(self):
        user1 = self.setup_user(enable_sharing=True)
        user2 = self.setup_user(enable_sharing=True)
        user3 = self.setup_user(enable_sharing=True)
        user4 = self.setup_user(enable_sharing=False)
        tag = self.setup_tag()

        shared_bookmarks = [
            self.setup_bookmark(user=user1, shared=True, title="test title"),
            self.setup_bookmark(user=user2, shared=True),
            self.setup_bookmark(user=user3, shared=True, tags=[tag]),
        ]

        # Unshared bookmarks
        self.setup_bookmark(user=user1, shared=False, title="test title"),
        self.setup_bookmark(user=user2, shared=False),
        self.setup_bookmark(user=user3, shared=False, tags=[tag]),
        self.setup_bookmark(user=user4, shared=True, tags=[tag]),

        # Should return shared bookmarks from all users
        query_set = queries.query_shared_bookmarks(
            None, self.profile, BookmarkSearch(q=""), False
        )
        self.assertQueryResult(query_set, [shared_bookmarks])

        # Should respect search query
        query_set = queries.query_shared_bookmarks(
            None, self.profile, BookmarkSearch(q="test title"), False
        )
        self.assertQueryResult(query_set, [[shared_bookmarks[0]]])

        query_set = queries.query_shared_bookmarks(
            None, self.profile, BookmarkSearch(q=f"#{tag.name}"), False
        )
        self.assertQueryResult(query_set, [[shared_bookmarks[2]]])

    def test_query_publicly_shared_bookmarks(self):
        user1 = self.setup_user(enable_sharing=True, enable_public_sharing=True)
        user2 = self.setup_user(enable_sharing=True)

        bookmark1 = self.setup_bookmark(user=user1, shared=True)
        self.setup_bookmark(user=user2, shared=True)

        query_set = queries.query_shared_bookmarks(
            None, self.profile, BookmarkSearch(q=""), True
        )
        self.assertQueryResult(query_set, [[bookmark1]])

    def test_query_shared_bookmark_tags(self):
        user1 = self.setup_user(enable_sharing=True)
        user2 = self.setup_user(enable_sharing=True)
        user3 = self.setup_user(enable_sharing=True)
        user4 = self.setup_user(enable_sharing=False)

        shared_tags = [
            self.setup_tag(user=user1),
            self.setup_tag(user=user2),
            self.setup_tag(user=user3),
        ]

        self.setup_bookmark(user=user1, shared=True, tags=[shared_tags[0]]),
        self.setup_bookmark(user=user2, shared=True, tags=[shared_tags[1]]),
        self.setup_bookmark(user=user3, shared=True, tags=[shared_tags[2]]),

        self.setup_bookmark(
            user=user1, shared=False, tags=[self.setup_tag(user=user1)]
        ),
        self.setup_bookmark(
            user=user2, shared=False, tags=[self.setup_tag(user=user2)]
        ),
        self.setup_bookmark(
            user=user3, shared=False, tags=[self.setup_tag(user=user3)]
        ),
        self.setup_bookmark(user=user4, shared=True, tags=[self.setup_tag(user=user4)]),

        query_set = queries.query_shared_bookmark_tags(
            None, self.profile, BookmarkSearch(q=""), False
        )

        self.assertQueryResult(query_set, [shared_tags])

    def test_query_publicly_shared_bookmark_tags(self):
        user1 = self.setup_user(enable_sharing=True, enable_public_sharing=True)
        user2 = self.setup_user(enable_sharing=True)

        tag1 = self.setup_tag(user=user1)
        tag2 = self.setup_tag(user=user2)

        self.setup_bookmark(user=user1, shared=True, tags=[tag1]),
        self.setup_bookmark(user=user2, shared=True, tags=[tag2]),

        query_set = queries.query_shared_bookmark_tags(
            None, self.profile, BookmarkSearch(q=""), True
        )

        self.assertQueryResult(query_set, [[tag1]])

    def test_query_shared_bookmark_users(self):
        users_with_shared_bookmarks = [
            self.setup_user(enable_sharing=True),
            self.setup_user(enable_sharing=True),
        ]
        users_without_shared_bookmarks = [
            self.setup_user(enable_sharing=True),
            self.setup_user(enable_sharing=True),
            self.setup_user(enable_sharing=False),
        ]

        # Shared bookmarks
        self.setup_bookmark(
            user=users_with_shared_bookmarks[0], shared=True, title="test title"
        ),
        self.setup_bookmark(user=users_with_shared_bookmarks[1], shared=True),

        # Unshared bookmarks
        self.setup_bookmark(
            user=users_without_shared_bookmarks[0], shared=False, title="test title"
        ),
        self.setup_bookmark(user=users_without_shared_bookmarks[1], shared=False),
        self.setup_bookmark(user=users_without_shared_bookmarks[2], shared=True),

        # Should return users with shared bookmarks
        query_set = queries.query_shared_bookmark_users(
            self.profile, BookmarkSearch(q=""), False
        )
        self.assertQueryResult(query_set, [users_with_shared_bookmarks])

        # Should respect search query
        query_set = queries.query_shared_bookmark_users(
            self.profile, BookmarkSearch(q="test title"), False
        )
        self.assertQueryResult(query_set, [[users_with_shared_bookmarks[0]]])

    def test_query_publicly_shared_bookmark_users(self):
        user1 = self.setup_user(enable_sharing=True, enable_public_sharing=True)
        user2 = self.setup_user(enable_sharing=True)

        self.setup_bookmark(user=user1, shared=True)
        self.setup_bookmark(user=user2, shared=True)

        query_set = queries.query_shared_bookmark_users(
            self.profile, BookmarkSearch(q=""), True
        )
        self.assertQueryResult(query_set, [[user1]])

    def test_sorty_by_date_added_asc(self):
        search = BookmarkSearch(sort=BookmarkSearch.SORT_ADDED_ASC)

        bookmarks = [
            self.setup_bookmark(
                added=timezone.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
            ),
            self.setup_bookmark(
                added=timezone.datetime(2021, 2, 1, tzinfo=datetime.timezone.utc)
            ),
            self.setup_bookmark(
                added=timezone.datetime(2022, 3, 1, tzinfo=datetime.timezone.utc)
            ),
            self.setup_bookmark(
                added=timezone.datetime(2023, 4, 1, tzinfo=datetime.timezone.utc)
            ),
            self.setup_bookmark(
                added=timezone.datetime(2022, 5, 1, tzinfo=datetime.timezone.utc)
            ),
            self.setup_bookmark(
                added=timezone.datetime(2021, 6, 1, tzinfo=datetime.timezone.utc)
            ),
            self.setup_bookmark(
                added=timezone.datetime(2020, 7, 1, tzinfo=datetime.timezone.utc)
            ),
        ]
        sorted_bookmarks = sorted(bookmarks, key=lambda b: b.date_added)

        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertEqual(list(query), sorted_bookmarks)

    def test_sorty_by_date_added_desc(self):
        search = BookmarkSearch(sort=BookmarkSearch.SORT_ADDED_DESC)

        bookmarks = [
            self.setup_bookmark(
                added=timezone.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
            ),
            self.setup_bookmark(
                added=timezone.datetime(2021, 2, 1, tzinfo=datetime.timezone.utc)
            ),
            self.setup_bookmark(
                added=timezone.datetime(2022, 3, 1, tzinfo=datetime.timezone.utc)
            ),
            self.setup_bookmark(
                added=timezone.datetime(2023, 4, 1, tzinfo=datetime.timezone.utc)
            ),
            self.setup_bookmark(
                added=timezone.datetime(2022, 5, 1, tzinfo=datetime.timezone.utc)
            ),
            self.setup_bookmark(
                added=timezone.datetime(2021, 6, 1, tzinfo=datetime.timezone.utc)
            ),
            self.setup_bookmark(
                added=timezone.datetime(2020, 7, 1, tzinfo=datetime.timezone.utc)
            ),
        ]
        sorted_bookmarks = sorted(bookmarks, key=lambda b: b.date_added, reverse=True)

        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertEqual(list(query), sorted_bookmarks)

    def setup_title_sort_data(self):
        # lots of combinations to test effective title logic
        bookmarks = [
            self.setup_bookmark(title="a_1_1"),
            self.setup_bookmark(title="A_1_2"),
            self.setup_bookmark(title="b_1_1"),
            self.setup_bookmark(title="B_1_2"),
            self.setup_bookmark(title="", website_title="a_2_1"),
            self.setup_bookmark(title="", website_title="A_2_2"),
            self.setup_bookmark(title="", website_title="b_2_1"),
            self.setup_bookmark(title="", website_title="B_2_2"),
            self.setup_bookmark(title="", website_title="", url="a_3_1"),
            self.setup_bookmark(title="", website_title="", url="A_3_2"),
            self.setup_bookmark(title="", website_title="", url="b_3_1"),
            self.setup_bookmark(title="", website_title="", url="B_3_2"),
            self.setup_bookmark(title="a_4_1", website_title="0"),
            self.setup_bookmark(title="A_4_2", website_title="0"),
            self.setup_bookmark(title="b_4_1", website_title="0"),
            self.setup_bookmark(title="B_4_2", website_title="0"),
            self.setup_bookmark(title="a_5_1", url="0"),
            self.setup_bookmark(title="A_5_2", url="0"),
            self.setup_bookmark(title="b_5_1", url="0"),
            self.setup_bookmark(title="B_5_2", url="0"),
            self.setup_bookmark(title="", website_title="a_6_1", url="0"),
            self.setup_bookmark(title="", website_title="A_6_2", url="0"),
            self.setup_bookmark(title="", website_title="b_6_1", url="0"),
            self.setup_bookmark(title="", website_title="B_6_2", url="0"),
            self.setup_bookmark(title="a_7_1", website_title="0", url="0"),
            self.setup_bookmark(title="A_7_2", website_title="0", url="0"),
            self.setup_bookmark(title="b_7_1", website_title="0", url="0"),
            self.setup_bookmark(title="B_7_2", website_title="0", url="0"),
        ]
        return bookmarks

    def test_sort_by_title_asc(self):
        search = BookmarkSearch(sort=BookmarkSearch.SORT_TITLE_ASC)

        bookmarks = self.setup_title_sort_data()
        sorted_bookmarks = sorted(bookmarks, key=lambda b: b.resolved_title.lower())

        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertEqual(list(query), sorted_bookmarks)

    def test_sort_by_title_desc(self):
        search = BookmarkSearch(sort=BookmarkSearch.SORT_TITLE_DESC)

        bookmarks = self.setup_title_sort_data()
        sorted_bookmarks = sorted(
            bookmarks, key=lambda b: b.resolved_title.lower(), reverse=True
        )

        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertEqual(list(query), sorted_bookmarks)

    def test_random_sort(self):
        search = BookmarkSearch(sort=BookmarkSearch.SORT_RANDOM)

        bookmarks = self.setup_title_sort_data()

        query1 = queries.query_bookmarks(self.user, self.profile, search)
        query2 = queries.query_bookmarks(self.user, self.profile, search)

        self.assertEqual(len(bookmarks), len(query1))
        self.assertEqual(len(bookmarks), len(query2))
        self.assertNotEqual(list(query1), list(query2))
