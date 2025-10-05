import datetime
import operator

from django.db.models import QuerySet
from django.test import TestCase
from django.utils import timezone

from bookmarks import queries
from bookmarks.models import BookmarkSearch, UserProfile
from bookmarks.tests.helpers import BookmarkFactoryMixin, random_sentence
from bookmarks.utils import unique


class QueriesBasicTestCase(TestCase, BookmarkFactoryMixin):
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
        ]
        self.tag1_bookmarks = [
            self.setup_bookmark(tags=[tag1]),
            self.setup_bookmark(title=random_sentence(), tags=[tag1]),
            self.setup_bookmark(description=random_sentence(), tags=[tag1]),
        ]
        self.tag1_as_term_bookmarks = [
            self.setup_bookmark(url="http://example.com/tag1"),
            self.setup_bookmark(title=random_sentence(including_word="tag1")),
            self.setup_bookmark(description=random_sentence(including_word="tag1")),
        ]
        self.term1_tag1_bookmarks = [
            self.setup_bookmark(url="http://example.com/term1", tags=[tag1]),
            self.setup_bookmark(
                title=random_sentence(including_word="term1"), tags=[tag1]
            ),
            self.setup_bookmark(
                description=random_sentence(including_word="term1"), tags=[tag1]
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
        ]
        self.tag1_bookmarks = [
            self.setup_bookmark(tags=[tag1, self.setup_tag()]),
            self.setup_bookmark(title=random_sentence(), tags=[tag1, self.setup_tag()]),
            self.setup_bookmark(
                description=random_sentence(), tags=[tag1, self.setup_tag()]
            ),
        ]
        self.tag1_as_term_bookmarks = [
            self.setup_bookmark(url="http://example.com/tag1"),
            self.setup_bookmark(title=random_sentence(including_word="tag1")),
            self.setup_bookmark(description=random_sentence(including_word="tag1")),
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
        ]
        self.tag2_bookmarks = [
            self.setup_bookmark(tags=[tag2, self.setup_tag()]),
        ]
        self.tag1_tag2_bookmarks = [
            self.setup_bookmark(tags=[tag1, tag2, self.setup_tag()]),
        ]

    def assertQueryResult(self, query: QuerySet, item_lists: list[list]):
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
        other_user = self.setup_user()
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
        other_user = self.setup_user()
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
        other_user = self.setup_user()
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
        other_user = self.setup_user()
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
            self.setup_bookmark(title="", url="a_3_1"),
            self.setup_bookmark(title="", url="A_3_2"),
            self.setup_bookmark(title="", url="b_3_1"),
            self.setup_bookmark(title="", url="B_3_2"),
            self.setup_bookmark(title="a_5_1", url="0"),
            self.setup_bookmark(title="A_5_2", url="0"),
            self.setup_bookmark(title="b_5_1", url="0"),
            self.setup_bookmark(title="B_5_2", url="0"),
            self.setup_bookmark(title="", url="0"),
            self.setup_bookmark(title="", url="0"),
            self.setup_bookmark(title="", url="0"),
            self.setup_bookmark(title="", url="0"),
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

    def test_query_bookmarks_filter_modified_since(self):
        # Create bookmarks with different modification dates
        older_bookmark = self.setup_bookmark(title="old bookmark")
        recent_bookmark = self.setup_bookmark(title="recent bookmark")

        # Modify date field on bookmark directly to test modified_since
        older_bookmark.date_modified = timezone.datetime(
            2025, 1, 1, tzinfo=datetime.timezone.utc
        )
        older_bookmark.save()
        recent_bookmark.date_modified = timezone.datetime(
            2025, 5, 15, tzinfo=datetime.timezone.utc
        )
        recent_bookmark.save()

        # Test with date between the two bookmarks
        search = BookmarkSearch(modified_since="2025-03-01T00:00:00Z")
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), [recent_bookmark])

        # Test with date before both bookmarks
        search = BookmarkSearch(modified_since="2024-12-31T00:00:00Z")
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), [older_bookmark, recent_bookmark])

        # Test with date after both bookmarks
        search = BookmarkSearch(modified_since="2025-05-16T00:00:00Z")
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), [])

        # Test with no modified_since - should return all bookmarks
        search = BookmarkSearch()
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), [older_bookmark, recent_bookmark])

        # Test with invalid date format - should be ignored
        search = BookmarkSearch(modified_since="invalid-date")
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), [older_bookmark, recent_bookmark])

    def test_query_bookmarks_filter_added_since(self):
        # Create bookmarks with different dates
        older_bookmark = self.setup_bookmark(
            title="old bookmark",
            added=timezone.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
        )
        recent_bookmark = self.setup_bookmark(
            title="recent bookmark",
            added=timezone.datetime(2025, 5, 15, tzinfo=datetime.timezone.utc),
        )

        # Test with date between the two bookmarks
        search = BookmarkSearch(added_since="2025-03-01T00:00:00Z")
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), [recent_bookmark])

        # Test with date before both bookmarks
        search = BookmarkSearch(added_since="2024-12-31T00:00:00Z")
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), [older_bookmark, recent_bookmark])

        # Test with date after both bookmarks
        search = BookmarkSearch(added_since="2025-05-16T00:00:00Z")
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), [])

        # Test with no added_since - should return all bookmarks
        search = BookmarkSearch()
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), [older_bookmark, recent_bookmark])

        # Test with invalid date format - should be ignored
        search = BookmarkSearch(added_since="invalid-date")
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), [older_bookmark, recent_bookmark])

    def test_query_bookmarks_with_bundle_search_terms(self):
        bundle = self.setup_bundle(search="search_term_A search_term_B")

        matching_bookmarks = [
            self.setup_bookmark(
                title="search_term_A content", description="search_term_B also here"
            ),
            self.setup_bookmark(url="http://example.com/search_term_A/search_term_B"),
        ]

        # Bookmarks that should not match
        self.setup_bookmark(title="search_term_A only")
        self.setup_bookmark(description="search_term_B only")
        self.setup_bookmark(title="unrelated content")

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="", bundle=bundle)
        )
        self.assertQueryResult(query, [matching_bookmarks])

    def test_query_bookmarks_with_search_and_bundle_search_terms(self):
        bundle = self.setup_bundle(search="bundle_term_B")
        search = BookmarkSearch(q="search_term_A", bundle=bundle)

        matching_bookmarks = [
            self.setup_bookmark(
                title="search_term_A content", description="bundle_term_B also here"
            )
        ]

        # Bookmarks that should not match
        self.setup_bookmark(title="search_term_A only")
        self.setup_bookmark(description="bundle_term_B only")
        self.setup_bookmark(title="unrelated content")

        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertQueryResult(query, [matching_bookmarks])

    def test_query_bookmarks_with_bundle_any_tags(self):
        bundle = self.setup_bundle(any_tags="bundleTag1 bundleTag2")

        tag1 = self.setup_tag(name="bundleTag1")
        tag2 = self.setup_tag(name="bundleTag2")
        other_tag = self.setup_tag(name="otherTag")

        matching_bookmarks = [
            self.setup_bookmark(tags=[tag1]),
            self.setup_bookmark(tags=[tag2]),
            self.setup_bookmark(tags=[tag1, tag2]),
        ]

        # Bookmarks that should not match
        self.setup_bookmark(tags=[other_tag])
        self.setup_bookmark()

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="", bundle=bundle)
        )
        self.assertQueryResult(query, [matching_bookmarks])

    def test_query_bookmarks_with_search_tags_and_bundle_any_tags(self):
        bundle = self.setup_bundle(any_tags="bundleTagA bundleTagB")
        search = BookmarkSearch(q="#searchTag1 #searchTag2", bundle=bundle)

        search_tag1 = self.setup_tag(name="searchTag1")
        search_tag2 = self.setup_tag(name="searchTag2")
        bundle_tag_a = self.setup_tag(name="bundleTagA")
        bundle_tag_b = self.setup_tag(name="bundleTagB")
        other_tag = self.setup_tag(name="otherTag")

        matching_bookmarks = [
            self.setup_bookmark(tags=[search_tag1, search_tag2, bundle_tag_a]),
            self.setup_bookmark(tags=[search_tag1, search_tag2, bundle_tag_b]),
            self.setup_bookmark(
                tags=[search_tag1, search_tag2, bundle_tag_a, bundle_tag_b]
            ),
        ]

        # Bookmarks that should not match
        self.setup_bookmark(tags=[search_tag1, search_tag2, other_tag])
        self.setup_bookmark(tags=[search_tag1, search_tag2])
        self.setup_bookmark(tags=[search_tag1, bundle_tag_a])
        self.setup_bookmark(tags=[search_tag2, bundle_tag_b])
        self.setup_bookmark(tags=[bundle_tag_a])
        self.setup_bookmark(tags=[bundle_tag_b])
        self.setup_bookmark(tags=[bundle_tag_a, bundle_tag_b])
        self.setup_bookmark(tags=[other_tag])
        self.setup_bookmark()

        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertQueryResult(query, [matching_bookmarks])

    def test_query_bookmarks_with_bundle_all_tags(self):
        bundle = self.setup_bundle(all_tags="bundleTag1 bundleTag2")

        tag1 = self.setup_tag(name="bundleTag1")
        tag2 = self.setup_tag(name="bundleTag2")
        other_tag = self.setup_tag(name="otherTag")

        matching_bookmarks = [self.setup_bookmark(tags=[tag1, tag2])]

        # Bookmarks that should not match
        self.setup_bookmark(tags=[tag1])
        self.setup_bookmark(tags=[tag2])
        self.setup_bookmark(tags=[tag1, other_tag])
        self.setup_bookmark(tags=[other_tag])
        self.setup_bookmark()

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="", bundle=bundle)
        )
        self.assertQueryResult(query, [matching_bookmarks])

    def test_query_bookmarks_with_search_tags_and_bundle_all_tags(self):
        bundle = self.setup_bundle(all_tags="bundleTagA bundleTagB")
        search = BookmarkSearch(q="#searchTag1 #searchTag2", bundle=bundle)

        search_tag1 = self.setup_tag(name="searchTag1")
        search_tag2 = self.setup_tag(name="searchTag2")
        bundle_tag_a = self.setup_tag(name="bundleTagA")
        bundle_tag_b = self.setup_tag(name="bundleTagB")
        other_tag = self.setup_tag(name="otherTag")

        matching_bookmarks = [
            self.setup_bookmark(
                tags=[search_tag1, search_tag2, bundle_tag_a, bundle_tag_b]
            )
        ]

        # Bookmarks that should not match
        self.setup_bookmark(tags=[search_tag1, search_tag2, bundle_tag_a])
        self.setup_bookmark(tags=[search_tag1, bundle_tag_a, bundle_tag_b])
        self.setup_bookmark(tags=[search_tag1, search_tag2])
        self.setup_bookmark(tags=[bundle_tag_a, bundle_tag_b])
        self.setup_bookmark(tags=[search_tag1, bundle_tag_a])
        self.setup_bookmark(tags=[other_tag])
        self.setup_bookmark()

        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertQueryResult(query, [matching_bookmarks])

    def test_query_bookmarks_with_bundle_excluded_tags(self):
        bundle = self.setup_bundle(excluded_tags="excludeTag1 excludeTag2")

        exclude_tag1 = self.setup_tag(name="excludeTag1")
        exclude_tag2 = self.setup_tag(name="excludeTag2")
        keep_tag = self.setup_tag(name="keepTag")
        keep_other_tag = self.setup_tag(name="keepOtherTag")

        matching_bookmarks = [
            self.setup_bookmark(tags=[keep_tag]),
            self.setup_bookmark(tags=[keep_other_tag]),
            self.setup_bookmark(tags=[keep_tag, keep_other_tag]),
            self.setup_bookmark(),
        ]

        # Bookmarks that should not be returned
        self.setup_bookmark(tags=[exclude_tag1])
        self.setup_bookmark(tags=[exclude_tag2])
        self.setup_bookmark(tags=[exclude_tag1, keep_tag])
        self.setup_bookmark(tags=[exclude_tag2, keep_tag])
        self.setup_bookmark(tags=[exclude_tag1, exclude_tag2])
        self.setup_bookmark(tags=[exclude_tag1, exclude_tag2, keep_tag])

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="", bundle=bundle)
        )
        self.assertQueryResult(query, [matching_bookmarks])

    def test_query_bookmarks_with_bundle_combined_tags(self):
        bundle = self.setup_bundle(
            any_tags="anyTagA anyTagB",
            all_tags="allTag1 allTag2",
            excluded_tags="excludedTag",
        )

        any_tag_a = self.setup_tag(name="anyTagA")
        any_tag_b = self.setup_tag(name="anyTagB")
        all_tag_1 = self.setup_tag(name="allTag1")
        all_tag_2 = self.setup_tag(name="allTag2")
        other_tag = self.setup_tag(name="otherTag")
        excluded_tag = self.setup_tag(name="excludedTag")

        matching_bookmarks = [
            self.setup_bookmark(tags=[any_tag_a, all_tag_1, all_tag_2]),
            self.setup_bookmark(tags=[any_tag_b, all_tag_1, all_tag_2]),
            self.setup_bookmark(tags=[any_tag_a, any_tag_b, all_tag_1, all_tag_2]),
            self.setup_bookmark(tags=[any_tag_a, all_tag_1, all_tag_2, other_tag]),
            self.setup_bookmark(tags=[any_tag_b, all_tag_1, all_tag_2, other_tag]),
        ]

        # Bookmarks that should not match
        self.setup_bookmark(tags=[any_tag_a, all_tag_1])
        self.setup_bookmark(tags=[any_tag_b, all_tag_2])
        self.setup_bookmark(tags=[any_tag_a, any_tag_b, all_tag_1])
        self.setup_bookmark(tags=[all_tag_1, all_tag_2])
        self.setup_bookmark(tags=[all_tag_1, all_tag_2, other_tag])
        self.setup_bookmark(tags=[any_tag_a])
        self.setup_bookmark(tags=[any_tag_b])
        self.setup_bookmark(tags=[all_tag_1])
        self.setup_bookmark(tags=[all_tag_2])
        self.setup_bookmark(tags=[any_tag_a, all_tag_1, all_tag_2, excluded_tag])
        self.setup_bookmark(tags=[any_tag_b, all_tag_1, all_tag_2, excluded_tag])
        self.setup_bookmark(tags=[other_tag])
        self.setup_bookmark()

        query = queries.query_bookmarks(
            self.user, self.profile, BookmarkSearch(q="", bundle=bundle)
        )
        self.assertQueryResult(query, [matching_bookmarks])

    def test_query_archived_bookmarks_with_bundle(self):
        bundle = self.setup_bundle(any_tags="bundleTag1 bundleTag2")

        tag1 = self.setup_tag(name="bundleTag1")
        tag2 = self.setup_tag(name="bundleTag2")
        other_tag = self.setup_tag(name="otherTag")

        matching_bookmarks = [
            self.setup_bookmark(is_archived=True, tags=[tag1]),
            self.setup_bookmark(is_archived=True, tags=[tag2]),
            self.setup_bookmark(is_archived=True, tags=[tag1, tag2]),
        ]

        # Bookmarks that should not match
        self.setup_bookmark(is_archived=True, tags=[other_tag])
        self.setup_bookmark(is_archived=True)
        self.setup_bookmark(tags=[tag1]),
        self.setup_bookmark(tags=[tag2]),
        self.setup_bookmark(tags=[tag1, tag2]),

        query = queries.query_archived_bookmarks(
            self.user, self.profile, BookmarkSearch(q="", bundle=bundle)
        )
        self.assertQueryResult(query, [matching_bookmarks])

    def test_query_shared_bookmarks_with_bundle(self):
        user1 = self.setup_user(enable_sharing=True)
        user2 = self.setup_user(enable_sharing=True)

        bundle = self.setup_bundle(any_tags="bundleTag1 bundleTag2")

        tag1 = self.setup_tag(name="bundleTag1")
        tag2 = self.setup_tag(name="bundleTag2")
        other_tag = self.setup_tag(name="otherTag")

        matching_bookmarks = [
            self.setup_bookmark(user=user1, shared=True, tags=[tag1]),
            self.setup_bookmark(user=user2, shared=True, tags=[tag2]),
            self.setup_bookmark(user=user1, shared=True, tags=[tag1, tag2]),
        ]

        # Bookmarks that should not match
        self.setup_bookmark(user=user1, shared=True, tags=[other_tag])
        self.setup_bookmark(user=user2, shared=True)
        self.setup_bookmark(user=user1, shared=False, tags=[tag1]),
        self.setup_bookmark(user=user2, shared=False, tags=[tag2]),
        self.setup_bookmark(user=user1, shared=False, tags=[tag1, tag2]),

        query = queries.query_shared_bookmarks(
            None, self.profile, BookmarkSearch(q="", bundle=bundle), False
        )
        self.assertQueryResult(query, [matching_bookmarks])


# Legacy search should be covered by basic test suite which was effectively the
# full test suite before advanced search was introduced.
class QueriesLegacySearchTestCase(QueriesBasicTestCase):
    def setUp(self):
        super().setUp()
        self.profile.legacy_search = True
        self.profile.save()


class QueriesAdvancedSearchTestCase(TestCase, BookmarkFactoryMixin):

    def setUp(self):
        self.user = self.get_or_create_test_user()
        self.profile = self.user.profile

        self.python_bookmark = self.setup_bookmark(
            title="Python Tutorial",
            tags=[self.setup_tag(name="python"), self.setup_tag(name="tutorial")],
        )
        self.java_bookmark = self.setup_bookmark(
            title="Java Guide",
            tags=[self.setup_tag(name="java"), self.setup_tag(name="programming")],
        )
        self.deprecated_python_bookmark = self.setup_bookmark(
            title="Old Python Guide",
            tags=[self.setup_tag(name="python"), self.setup_tag(name="deprecated")],
        )
        self.javascript_tutorial = self.setup_bookmark(
            title="JavaScript Basics",
            tags=[self.setup_tag(name="javascript"), self.setup_tag(name="tutorial")],
        )
        self.web_development = self.setup_bookmark(
            title="Web Development with React",
            description="Modern web development",
            tags=[self.setup_tag(name="react"), self.setup_tag(name="web")],
        )

    def test_explicit_and_operator(self):
        search = BookmarkSearch(q="python AND tutorial")
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), [self.python_bookmark])

    def test_or_operator(self):
        search = BookmarkSearch(q="#python OR #java")
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(
            list(query),
            [self.python_bookmark, self.java_bookmark, self.deprecated_python_bookmark],
        )

    def test_not_operator(self):
        search = BookmarkSearch(q="#python AND NOT #deprecated")
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), [self.python_bookmark])

    def test_implicit_and_between_terms(self):
        search = BookmarkSearch(q="web development")
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), [self.web_development])

        search = BookmarkSearch(q="python tutorial")
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), [self.python_bookmark])

    def test_implicit_and_between_tags(self):
        search = BookmarkSearch(q="#python #tutorial")
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), [self.python_bookmark])

    def test_nested_and_expression(self):
        search = BookmarkSearch(q="nonexistingterm OR (#python AND #tutorial)")
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), [self.python_bookmark])

        search = BookmarkSearch(
            q="(#javascript AND #tutorial) OR (#python AND #tutorial)"
        )
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(
            list(query), [self.javascript_tutorial, self.python_bookmark]
        )

    def test_mixed_terms_and_tags_with_operators(self):
        # Set lax mode to allow term matching against tags
        self.profile.tag_search = self.profile.TAG_SEARCH_LAX
        self.profile.save()

        search = BookmarkSearch(q="(tutorial OR guide) AND #python")
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(
            list(query), [self.python_bookmark, self.deprecated_python_bookmark]
        )

    def test_parentheses(self):
        # Set lax mode to allow term matching against tags
        self.profile.tag_search = self.profile.TAG_SEARCH_LAX
        self.profile.save()

        # Without parentheses
        search = BookmarkSearch(q="python AND tutorial OR javascript AND tutorial")
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(
            list(query), [self.python_bookmark, self.javascript_tutorial]
        )

        # With parentheses
        search = BookmarkSearch(q="(python OR javascript) AND tutorial")
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(
            list(query), [self.python_bookmark, self.javascript_tutorial]
        )

    def test_complex_query_with_all_operators(self):
        # Set lax mode to allow term matching against tags
        self.profile.tag_search = self.profile.TAG_SEARCH_LAX
        self.profile.save()

        search = BookmarkSearch(
            q="(#python OR #javascript) AND tutorial AND NOT #deprecated"
        )
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(
            list(query), [self.python_bookmark, self.javascript_tutorial]
        )

    def test_quoted_strings_with_operators(self):
        # Set lax mode to allow term matching against tags
        self.profile.tag_search = self.profile.TAG_SEARCH_LAX
        self.profile.save()

        search = BookmarkSearch(q='"Web Development" OR tutorial')
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(
            list(query),
            [self.web_development, self.python_bookmark, self.javascript_tutorial],
        )

    def test_implicit_and_with_quoted_strings(self):
        search = BookmarkSearch(q='"Web Development" react')
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), [self.web_development])

    def test_empty_query(self):
        # empty query returns all bookmarks
        search = BookmarkSearch(q="")
        query = queries.query_bookmarks(self.user, self.profile, search)
        expected = [
            self.python_bookmark,
            self.java_bookmark,
            self.deprecated_python_bookmark,
            self.javascript_tutorial,
            self.web_development,
        ]
        self.assertCountEqual(list(query), expected)

    def test_unparseable_query_returns_no_results(self):
        # Use a query that causes a parse error (unclosed parenthesis)
        search = BookmarkSearch(q="(python AND tutorial")
        query = queries.query_bookmarks(self.user, self.profile, search)
        self.assertCountEqual(list(query), [])


class GetTagsForQueryTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self):
        self.user = self.get_or_create_test_user()
        self.profile = self.user.profile

    def test_returns_tags_matching_query(self):
        python_tag = self.setup_tag(name="python")
        django_tag = self.setup_tag(name="django")
        self.setup_tag(name="unused")

        result = queries.get_tags_for_query(
            self.user, self.profile, "#python and #django"
        )
        self.assertCountEqual(list(result), [python_tag, django_tag])

    def test_case_insensitive_matching(self):
        python_tag = self.setup_tag(name="Python")

        result = queries.get_tags_for_query(self.user, self.profile, "#python")
        self.assertCountEqual(list(result), [python_tag])

        # having two tags with the same name returns both for now
        other_python_tag = self.setup_tag(name="python")

        result = queries.get_tags_for_query(self.user, self.profile, "#python")
        self.assertCountEqual(list(result), [python_tag, other_python_tag])

    def test_lax_mode_includes_terms(self):
        python_tag = self.setup_tag(name="python")
        django_tag = self.setup_tag(name="django")

        self.profile.tag_search = UserProfile.TAG_SEARCH_LAX
        self.profile.save()

        result = queries.get_tags_for_query(
            self.user, self.profile, "#python and django"
        )
        self.assertCountEqual(list(result), [python_tag, django_tag])

    def test_strict_mode_excludes_terms(self):
        python_tag = self.setup_tag(name="python")
        self.setup_tag(name="django")

        result = queries.get_tags_for_query(
            self.user, self.profile, "#python and django"
        )
        self.assertCountEqual(list(result), [python_tag])

    def test_only_returns_user_tags(self):
        python_tag = self.setup_tag(name="python")

        other_user = self.setup_user()
        other_python = self.setup_tag(name="python", user=other_user)
        other_django = self.setup_tag(name="django", user=other_user)

        result = queries.get_tags_for_query(
            self.user, self.profile, "#python and #django"
        )
        self.assertCountEqual(list(result), [python_tag])
        self.assertNotIn(other_python, list(result))
        self.assertNotIn(other_django, list(result))

    def test_empty_query_returns_no_tags(self):
        self.setup_tag(name="python")

        result = queries.get_tags_for_query(self.user, self.profile, "")
        self.assertCountEqual(list(result), [])

    def test_query_with_no_tags_returns_empty(self):
        self.setup_tag(name="python")

        result = queries.get_tags_for_query(self.user, self.profile, "!unread")
        self.assertCountEqual(list(result), [])

    def test_nonexistent_tag_returns_empty(self):
        self.setup_tag(name="python")

        result = queries.get_tags_for_query(self.user, self.profile, "#ruby")
        self.assertCountEqual(list(result), [])


class GetSharedTagsForQueryTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self):
        self.user = self.get_or_create_test_user()
        self.profile = self.user.profile
        self.profile.enable_sharing = True
        self.profile.save()

    def test_returns_tags_from_shared_bookmarks(self):
        python_tag = self.setup_tag(name="python")
        self.setup_tag(name="django")
        self.setup_bookmark(shared=True, tags=[python_tag])

        result = queries.get_shared_tags_for_query(
            None, self.profile, "#python and #django", public_only=False
        )
        self.assertCountEqual(list(result), [python_tag])

    def test_excludes_tags_from_non_shared_bookmarks(self):
        python_tag = self.setup_tag(name="python")
        self.setup_tag(name="django")
        self.setup_bookmark(shared=False, tags=[python_tag])

        result = queries.get_shared_tags_for_query(
            None, self.profile, "#python and #django", public_only=False
        )
        self.assertCountEqual(list(result), [])

    def test_respects_sharing_enabled_setting(self):
        self.profile.enable_sharing = False
        self.profile.save()

        python_tag = self.setup_tag(name="python")
        self.setup_tag(name="django")
        self.setup_bookmark(shared=True, tags=[python_tag])

        result = queries.get_shared_tags_for_query(
            None, self.profile, "#python and #django", public_only=False
        )
        self.assertCountEqual(list(result), [])

    def test_public_only_flag(self):
        # public sharing disabled
        python_tag = self.setup_tag(name="python")
        self.setup_tag(name="django")
        self.setup_bookmark(shared=True, tags=[python_tag])

        result = queries.get_shared_tags_for_query(
            None, self.profile, "#python and #django", public_only=True
        )
        self.assertCountEqual(list(result), [])

        # public sharing enabled
        self.profile.enable_public_sharing = True
        self.profile.save()

        result = queries.get_shared_tags_for_query(
            None, self.profile, "#python and #django", public_only=True
        )
        self.assertCountEqual(list(result), [python_tag])

    def test_filters_by_user(self):
        python_tag = self.setup_tag(name="python")
        self.setup_tag(name="django")
        self.setup_bookmark(shared=True, tags=[python_tag])

        other_user = self.setup_user()
        other_user.profile.enable_sharing = True
        other_user.profile.save()
        other_tag = self.setup_tag(name="python", user=other_user)
        self.setup_bookmark(shared=True, tags=[other_tag], user=other_user)

        result = queries.get_shared_tags_for_query(
            self.user, self.profile, "#python and #django", public_only=False
        )
        self.assertCountEqual(list(result), [python_tag])
        self.assertNotIn(other_tag, list(result))
