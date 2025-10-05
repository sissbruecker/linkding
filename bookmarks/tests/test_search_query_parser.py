from django.test import TestCase

from bookmarks.services.search_query_parser import (
    SearchQueryTokenizer,
    TokenType,
    SearchExpression,
    TermExpression,
    TagExpression,
    SpecialKeywordExpression,
    AndExpression,
    OrExpression,
    NotExpression,
    SearchQueryParseError,
    parse_search_query,
    expression_to_string,
    strip_tag_from_query,
    extract_tag_names_from_query,
)
from bookmarks.models import UserProfile


def _term(term: str) -> TermExpression:
    return TermExpression(term)


def _tag(tag: str) -> TagExpression:
    return TagExpression(tag)


def _and(left: SearchExpression, right: SearchExpression) -> AndExpression:
    return AndExpression(left, right)


def _or(left: SearchExpression, right: SearchExpression) -> OrExpression:
    return OrExpression(left, right)


def _not(operand: SearchExpression) -> NotExpression:
    return NotExpression(operand)


def _keyword(keyword: str) -> SpecialKeywordExpression:
    return SpecialKeywordExpression(keyword)


class SearchQueryTokenizerTest(TestCase):
    def test_empty_query(self):
        tokenizer = SearchQueryTokenizer("")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.EOF)

    def test_whitespace_only_query(self):
        tokenizer = SearchQueryTokenizer("   ")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.EOF)

    def test_single_term(self):
        tokenizer = SearchQueryTokenizer("programming")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[0].type, TokenType.TERM)
        self.assertEqual(tokens[0].value, "programming")
        self.assertEqual(tokens[1].type, TokenType.EOF)

    def test_multiple_terms(self):
        tokenizer = SearchQueryTokenizer("programming books streaming")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 4)
        self.assertEqual(tokens[0].type, TokenType.TERM)
        self.assertEqual(tokens[0].value, "programming")
        self.assertEqual(tokens[1].type, TokenType.TERM)
        self.assertEqual(tokens[1].value, "books")
        self.assertEqual(tokens[2].type, TokenType.TERM)
        self.assertEqual(tokens[2].value, "streaming")
        self.assertEqual(tokens[3].type, TokenType.EOF)

    def test_hyphenated_term(self):
        tokenizer = SearchQueryTokenizer("client-side")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[0].type, TokenType.TERM)
        self.assertEqual(tokens[0].value, "client-side")
        self.assertEqual(tokens[1].type, TokenType.EOF)

    def test_and_operator(self):
        tokenizer = SearchQueryTokenizer("programming and books")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 4)
        self.assertEqual(tokens[0].type, TokenType.TERM)
        self.assertEqual(tokens[0].value, "programming")
        self.assertEqual(tokens[1].type, TokenType.AND)
        self.assertEqual(tokens[1].value, "and")
        self.assertEqual(tokens[2].type, TokenType.TERM)
        self.assertEqual(tokens[2].value, "books")
        self.assertEqual(tokens[3].type, TokenType.EOF)

    def test_or_operator(self):
        tokenizer = SearchQueryTokenizer("programming or books")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 4)
        self.assertEqual(tokens[0].type, TokenType.TERM)
        self.assertEqual(tokens[0].value, "programming")
        self.assertEqual(tokens[1].type, TokenType.OR)
        self.assertEqual(tokens[1].value, "or")
        self.assertEqual(tokens[2].type, TokenType.TERM)
        self.assertEqual(tokens[2].value, "books")
        self.assertEqual(tokens[3].type, TokenType.EOF)

    def test_not_operator(self):
        tokenizer = SearchQueryTokenizer("programming not books")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 4)
        self.assertEqual(tokens[0].type, TokenType.TERM)
        self.assertEqual(tokens[0].value, "programming")
        self.assertEqual(tokens[1].type, TokenType.NOT)
        self.assertEqual(tokens[1].value, "not")
        self.assertEqual(tokens[2].type, TokenType.TERM)
        self.assertEqual(tokens[2].value, "books")
        self.assertEqual(tokens[3].type, TokenType.EOF)

    def test_case_insensitive_operators(self):
        tokenizer = SearchQueryTokenizer(
            "programming AND books OR streaming NOT videos"
        )
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 8)
        self.assertEqual(tokens[1].type, TokenType.AND)
        self.assertEqual(tokens[3].type, TokenType.OR)
        self.assertEqual(tokens[5].type, TokenType.NOT)

    def test_parentheses(self):
        tokenizer = SearchQueryTokenizer("(programming or books) and streaming")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 8)
        self.assertEqual(tokens[0].type, TokenType.LPAREN)
        self.assertEqual(tokens[1].type, TokenType.TERM)
        self.assertEqual(tokens[1].value, "programming")
        self.assertEqual(tokens[2].type, TokenType.OR)
        self.assertEqual(tokens[3].type, TokenType.TERM)
        self.assertEqual(tokens[3].value, "books")
        self.assertEqual(tokens[4].type, TokenType.RPAREN)
        self.assertEqual(tokens[5].type, TokenType.AND)
        self.assertEqual(tokens[6].type, TokenType.TERM)
        self.assertEqual(tokens[6].value, "streaming")
        self.assertEqual(tokens[7].type, TokenType.EOF)

    def test_operator_as_part_of_term(self):
        # Terms containing operator words should be treated as terms
        tokenizer = SearchQueryTokenizer("android notarization")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 3)
        self.assertEqual(tokens[0].type, TokenType.TERM)
        self.assertEqual(tokens[0].value, "android")
        self.assertEqual(tokens[1].type, TokenType.TERM)
        self.assertEqual(tokens[1].value, "notarization")
        self.assertEqual(tokens[2].type, TokenType.EOF)

    def test_extra_whitespace(self):
        tokenizer = SearchQueryTokenizer("  programming   and    books  ")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 4)
        self.assertEqual(tokens[0].type, TokenType.TERM)
        self.assertEqual(tokens[0].value, "programming")
        self.assertEqual(tokens[1].type, TokenType.AND)
        self.assertEqual(tokens[2].type, TokenType.TERM)
        self.assertEqual(tokens[2].value, "books")
        self.assertEqual(tokens[3].type, TokenType.EOF)

    def test_quoted_strings(self):
        # Double quotes
        tokenizer = SearchQueryTokenizer('"good and bad"')
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[0].type, TokenType.TERM)
        self.assertEqual(tokens[0].value, "good and bad")
        self.assertEqual(tokens[1].type, TokenType.EOF)

        # Single quotes
        tokenizer = SearchQueryTokenizer("'hello world'")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[0].type, TokenType.TERM)
        self.assertEqual(tokens[0].value, "hello world")
        self.assertEqual(tokens[1].type, TokenType.EOF)

    def test_quoted_strings_with_operators(self):
        tokenizer = SearchQueryTokenizer('"good and bad" or programming')
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 4)
        self.assertEqual(tokens[0].type, TokenType.TERM)
        self.assertEqual(tokens[0].value, "good and bad")
        self.assertEqual(tokens[1].type, TokenType.OR)
        self.assertEqual(tokens[2].type, TokenType.TERM)
        self.assertEqual(tokens[2].value, "programming")
        self.assertEqual(tokens[3].type, TokenType.EOF)

    def test_escaped_quotes(self):
        # Escaped double quote within double quotes
        tokenizer = SearchQueryTokenizer('"say \\"hello\\""')
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[0].type, TokenType.TERM)
        self.assertEqual(tokens[0].value, 'say "hello"')
        self.assertEqual(tokens[1].type, TokenType.EOF)

        # Escaped single quote within single quotes
        tokenizer = SearchQueryTokenizer("'don\\'t worry'")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[0].type, TokenType.TERM)
        self.assertEqual(tokens[0].value, "don't worry")
        self.assertEqual(tokens[1].type, TokenType.EOF)

    def test_unclosed_quotes(self):
        # Unclosed quote should be handled gracefully
        tokenizer = SearchQueryTokenizer('"unclosed quote')
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[0].type, TokenType.TERM)
        self.assertEqual(tokens[0].value, "unclosed quote")
        self.assertEqual(tokens[1].type, TokenType.EOF)

    def test_tags(self):
        # Basic tag
        tokenizer = SearchQueryTokenizer("#python")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[0].type, TokenType.TAG)
        self.assertEqual(tokens[0].value, "python")
        self.assertEqual(tokens[1].type, TokenType.EOF)

        # Tag with hyphens
        tokenizer = SearchQueryTokenizer("#machine-learning")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[0].type, TokenType.TAG)
        self.assertEqual(tokens[0].value, "machine-learning")
        self.assertEqual(tokens[1].type, TokenType.EOF)

    def test_tags_with_operators(self):
        tokenizer = SearchQueryTokenizer("#python and #django")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 4)
        self.assertEqual(tokens[0].type, TokenType.TAG)
        self.assertEqual(tokens[0].value, "python")
        self.assertEqual(tokens[1].type, TokenType.AND)
        self.assertEqual(tokens[2].type, TokenType.TAG)
        self.assertEqual(tokens[2].value, "django")
        self.assertEqual(tokens[3].type, TokenType.EOF)

    def test_tags_mixed_with_terms(self):
        tokenizer = SearchQueryTokenizer("programming and #python and web")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 6)
        self.assertEqual(tokens[0].type, TokenType.TERM)
        self.assertEqual(tokens[0].value, "programming")
        self.assertEqual(tokens[1].type, TokenType.AND)
        self.assertEqual(tokens[2].type, TokenType.TAG)
        self.assertEqual(tokens[2].value, "python")
        self.assertEqual(tokens[3].type, TokenType.AND)
        self.assertEqual(tokens[4].type, TokenType.TERM)
        self.assertEqual(tokens[4].value, "web")
        self.assertEqual(tokens[5].type, TokenType.EOF)

    def test_empty_tag(self):
        # Tag with just # should be ignored (no token created)
        tokenizer = SearchQueryTokenizer("# ")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.EOF)

        # Empty tag at end of string
        tokenizer = SearchQueryTokenizer("#")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.EOF)

        # Empty tag mixed with other terms
        tokenizer = SearchQueryTokenizer("python # and django")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 4)
        self.assertEqual(tokens[0].type, TokenType.TERM)
        self.assertEqual(tokens[0].value, "python")
        self.assertEqual(tokens[1].type, TokenType.AND)
        self.assertEqual(tokens[2].type, TokenType.TERM)
        self.assertEqual(tokens[2].value, "django")
        self.assertEqual(tokens[3].type, TokenType.EOF)

    def test_special_keywords(self):
        tokenizer = SearchQueryTokenizer("!unread")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[0].type, TokenType.SPECIAL_KEYWORD)
        self.assertEqual(tokens[0].value, "unread")
        self.assertEqual(tokens[1].type, TokenType.EOF)

        tokenizer = SearchQueryTokenizer("!untagged")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[0].type, TokenType.SPECIAL_KEYWORD)
        self.assertEqual(tokens[0].value, "untagged")
        self.assertEqual(tokens[1].type, TokenType.EOF)

    def test_special_keywords_with_operators(self):
        tokenizer = SearchQueryTokenizer("!unread and !untagged")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 4)
        self.assertEqual(tokens[0].type, TokenType.SPECIAL_KEYWORD)
        self.assertEqual(tokens[0].value, "unread")
        self.assertEqual(tokens[1].type, TokenType.AND)
        self.assertEqual(tokens[2].type, TokenType.SPECIAL_KEYWORD)
        self.assertEqual(tokens[2].value, "untagged")
        self.assertEqual(tokens[3].type, TokenType.EOF)

    def test_special_keywords_mixed_with_terms_and_tags(self):
        tokenizer = SearchQueryTokenizer("!unread and #python and tutorial")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 6)
        self.assertEqual(tokens[0].type, TokenType.SPECIAL_KEYWORD)
        self.assertEqual(tokens[0].value, "unread")
        self.assertEqual(tokens[1].type, TokenType.AND)
        self.assertEqual(tokens[2].type, TokenType.TAG)
        self.assertEqual(tokens[2].value, "python")
        self.assertEqual(tokens[3].type, TokenType.AND)
        self.assertEqual(tokens[4].type, TokenType.TERM)
        self.assertEqual(tokens[4].value, "tutorial")
        self.assertEqual(tokens[5].type, TokenType.EOF)

    def test_empty_special_keyword(self):
        # Special keyword with just ! should be ignored (no token created)
        tokenizer = SearchQueryTokenizer("! ")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.EOF)

        # Empty special keyword at end of string
        tokenizer = SearchQueryTokenizer("!")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.EOF)


class SearchQueryParserTest(TestCase):
    """Test cases for the search query parser."""

    def test_empty_query(self):
        result = parse_search_query("")
        self.assertIsNone(result)

    def test_whitespace_only_query(self):
        result = parse_search_query("   ")
        self.assertIsNone(result)

    def test_single_term(self):
        result = parse_search_query("programming")
        expected = _term("programming")
        self.assertEqual(result, expected)

    def test_and_expression(self):
        result = parse_search_query("programming and books")
        expected = _and(_term("programming"), _term("books"))
        self.assertEqual(result, expected)

    def test_or_expression(self):
        result = parse_search_query("programming or books")
        expected = _or(_term("programming"), _term("books"))
        self.assertEqual(result, expected)

    def test_not_expression(self):
        result = parse_search_query("not programming")
        expected = _not(_term("programming"))
        self.assertEqual(result, expected)

    def test_operator_precedence_and_over_or(self):
        # "a or b and c" should parse as "a or (b and c)"
        result = parse_search_query("programming or books and streaming")
        expected = _or(_term("programming"), _and(_term("books"), _term("streaming")))
        self.assertEqual(result, expected)

    def test_operator_precedence_not_over_and(self):
        # "not a and b" should parse as "(not a) and b"
        result = parse_search_query("not programming and books")
        expected = _and(_not(_term("programming")), _term("books"))
        self.assertEqual(result, expected)

    def test_multiple_and_operators(self):
        # "a and b and c" should parse as "(a and b) and c" (left associative)
        result = parse_search_query("programming and books and streaming")
        expected = _and(_and(_term("programming"), _term("books")), _term("streaming"))
        self.assertEqual(result, expected)

    def test_multiple_or_operators(self):
        # "a or b or c" should parse as "(a or b) or c" (left associative)
        result = parse_search_query("programming or books or streaming")
        expected = _or(_or(_term("programming"), _term("books")), _term("streaming"))
        self.assertEqual(result, expected)

    def test_multiple_not_operators(self):
        result = parse_search_query("not not programming")
        expected = _not(_not(_term("programming")))
        self.assertEqual(result, expected)

    def test_parentheses_basic(self):
        result = parse_search_query("(programming)")
        expected = _term("programming")
        self.assertEqual(result, expected)

    def test_parentheses_change_precedence(self):
        # "(a or b) and c" should parse as "(a or b) and c"
        result = parse_search_query("(programming or books) and streaming")
        expected = _and(_or(_term("programming"), _term("books")), _term("streaming"))
        self.assertEqual(result, expected)

    def test_nested_parentheses(self):
        result = parse_search_query("((programming))")
        expected = _term("programming")
        self.assertEqual(result, expected)

    def test_complex_expression(self):
        result = parse_search_query(
            "programming and (books or streaming) and not client-side"
        )
        # Should be parsed as "(programming and (books or streaming)) and (not client-side)"
        expected = _and(
            _and(_term("programming"), _or(_term("books"), _term("streaming"))),
            _not(_term("client-side")),
        )
        self.assertEqual(result, expected)

    def test_hyphenated_terms(self):
        result = parse_search_query("client-side")
        expected = _term("client-side")
        self.assertEqual(result, expected)

    def test_case_insensitive_operators(self):
        result = parse_search_query("programming AND books OR streaming")
        expected = _or(_and(_term("programming"), _term("books")), _term("streaming"))
        self.assertEqual(result, expected)

        # Test implicit AND with NOT
        result = parse_search_query("programming AND books OR streaming NOT videos")
        expected = _or(
            _and(_term("programming"), _term("books")),
            _and(_term("streaming"), _not(_term("videos"))),
        )
        self.assertEqual(result, expected)

    def test_case_insensitive_operators_with_explicit_operators(self):
        result = parse_search_query("programming AND books OR streaming AND NOT videos")
        # Should parse as: (programming AND books) OR (streaming AND (NOT videos))
        expected = _or(
            _and(_term("programming"), _term("books")),
            _and(_term("streaming"), _not(_term("videos"))),
        )
        self.assertEqual(result, expected)

    def test_single_character_terms(self):
        result = parse_search_query("a and b")
        expected = _and(_term("a"), _term("b"))
        self.assertEqual(result, expected)

    def test_numeric_terms(self):
        result = parse_search_query("123 and 456")
        expected = _and(_term("123"), _term("456"))
        self.assertEqual(result, expected)

    def test_special_characters_in_terms(self):
        result = parse_search_query("test@example.com and file.txt")
        expected = _and(_term("test@example.com"), _term("file.txt"))
        self.assertEqual(result, expected)

    def test_url_terms(self):
        result = parse_search_query("https://example.com/foo/bar")
        expected = _term("https://example.com/foo/bar")
        self.assertEqual(result, expected)

    def test_url_with_operators(self):
        result = parse_search_query("https://github.com or https://gitlab.com")
        expected = _or(_term("https://github.com"), _term("https://gitlab.com"))
        self.assertEqual(result, expected)

    def test_quoted_strings(self):
        # Basic quoted string
        result = parse_search_query('"good and bad"')
        expected = _term("good and bad")
        self.assertEqual(result, expected)

        # Single quotes
        result = parse_search_query("'hello world'")
        expected = _term("hello world")
        self.assertEqual(result, expected)

    def test_quoted_strings_with_operators(self):
        # Quoted string with OR
        result = parse_search_query('"good and bad" or programming')
        expected = _or(_term("good and bad"), _term("programming"))
        self.assertEqual(result, expected)

        # Quoted string with AND
        result = parse_search_query('documentation and "API reference"')
        expected = _and(_term("documentation"), _term("API reference"))
        self.assertEqual(result, expected)

        # Quoted string with NOT
        result = parse_search_query('programming and not "bad practices"')
        expected = _and(_term("programming"), _not(_term("bad practices")))
        self.assertEqual(result, expected)

    def test_multiple_quoted_strings(self):
        result = parse_search_query('"hello world" and "goodbye moon"')
        expected = _and(_term("hello world"), _term("goodbye moon"))
        self.assertEqual(result, expected)

    def test_quoted_strings_with_parentheses(self):
        result = parse_search_query('("good morning" or "good evening") and coffee')
        expected = _and(
            _or(_term("good morning"), _term("good evening")), _term("coffee")
        )
        self.assertEqual(result, expected)

    def test_escaped_quotes_in_terms(self):
        result = parse_search_query('"say \\"hello\\""')
        expected = _term('say "hello"')
        self.assertEqual(result, expected)

    def test_tags(self):
        # Basic tag
        result = parse_search_query("#python")
        expected = _tag("python")
        self.assertEqual(result, expected)

        # Tag with hyphens
        result = parse_search_query("#machine-learning")
        expected = _tag("machine-learning")
        self.assertEqual(result, expected)

    def test_tags_with_operators(self):
        # Tag with AND
        result = parse_search_query("#python and #django")
        expected = _and(_tag("python"), _tag("django"))
        self.assertEqual(result, expected)

        # Tag with OR
        result = parse_search_query("#frontend or #backend")
        expected = _or(_tag("frontend"), _tag("backend"))
        self.assertEqual(result, expected)

        # Tag with NOT
        result = parse_search_query("not #deprecated")
        expected = _not(_tag("deprecated"))
        self.assertEqual(result, expected)

    def test_tags_mixed_with_terms(self):
        result = parse_search_query("programming and #python and tutorial")
        expected = _and(_and(_term("programming"), _tag("python")), _term("tutorial"))
        self.assertEqual(result, expected)

    def test_tags_with_quoted_strings(self):
        result = parse_search_query('"machine learning" and #python')
        expected = _and(_term("machine learning"), _tag("python"))
        self.assertEqual(result, expected)

    def test_tags_with_parentheses(self):
        result = parse_search_query("(#frontend or #backend) and javascript")
        expected = _and(_or(_tag("frontend"), _tag("backend")), _term("javascript"))
        self.assertEqual(result, expected)

    def test_empty_tags_ignored(self):
        # Test single empty tag
        result = parse_search_query("#")
        expected = None  # Empty query
        self.assertEqual(result, expected)

        # Test query that's just an empty tag and whitespace
        result = parse_search_query("# ")
        expected = None  # Empty query
        self.assertEqual(result, expected)

    def test_special_keywords(self):
        result = parse_search_query("!unread")
        expected = _keyword("unread")
        self.assertEqual(result, expected)

        result = parse_search_query("!untagged")
        expected = _keyword("untagged")
        self.assertEqual(result, expected)

    def test_special_keywords_with_operators(self):
        # Special keyword with AND
        result = parse_search_query("!unread and !untagged")
        expected = _and(_keyword("unread"), _keyword("untagged"))
        self.assertEqual(result, expected)

        # Special keyword with OR
        result = parse_search_query("!unread or !untagged")
        expected = _or(_keyword("unread"), _keyword("untagged"))
        self.assertEqual(result, expected)

        # Special keyword with NOT
        result = parse_search_query("not !unread")
        expected = _not(_keyword("unread"))
        self.assertEqual(result, expected)

    def test_special_keywords_mixed_with_terms_and_tags(self):
        result = parse_search_query("!unread and #python and tutorial")
        expected = _and(_and(_keyword("unread"), _tag("python")), _term("tutorial"))
        self.assertEqual(result, expected)

    def test_special_keywords_with_quoted_strings(self):
        result = parse_search_query('"machine learning" and !unread')
        expected = _and(_term("machine learning"), _keyword("unread"))
        self.assertEqual(result, expected)

    def test_special_keywords_with_parentheses(self):
        result = parse_search_query("(!unread or !untagged) and javascript")
        expected = _and(
            _or(_keyword("unread"), _keyword("untagged")), _term("javascript")
        )
        self.assertEqual(result, expected)

    def test_special_keywords_within_quoted_string(self):
        result = parse_search_query("'!unread and !untagged'")
        expected = _term("!unread and !untagged")
        self.assertEqual(result, expected)

    def test_implicit_and_basic(self):
        # Basic implicit AND between terms
        result = parse_search_query("programming book")
        expected = _and(_term("programming"), _term("book"))
        self.assertEqual(result, expected)

        # Three terms with implicit AND
        result = parse_search_query("python machine learning")
        expected = _and(_and(_term("python"), _term("machine")), _term("learning"))
        self.assertEqual(result, expected)

    def test_implicit_and_with_tags(self):
        # Implicit AND between term and tag
        result = parse_search_query("tutorial #python")
        expected = _and(_term("tutorial"), _tag("python"))
        self.assertEqual(result, expected)

        # Implicit AND between tag and term
        result = parse_search_query("#javascript tutorial")
        expected = _and(_tag("javascript"), _term("tutorial"))
        self.assertEqual(result, expected)

        # Multiple tags with implicit AND
        result = parse_search_query("#python #django #tutorial")
        expected = _and(_and(_tag("python"), _tag("django")), _tag("tutorial"))
        self.assertEqual(result, expected)

    def test_implicit_and_with_quoted_strings(self):
        # Implicit AND with quoted strings
        result = parse_search_query('"machine learning" tutorial')
        expected = _and(_term("machine learning"), _term("tutorial"))
        self.assertEqual(result, expected)

        # Mixed types with implicit AND
        result = parse_search_query('"deep learning" #python tutorial')
        expected = _and(_and(_term("deep learning"), _tag("python")), _term("tutorial"))
        self.assertEqual(result, expected)

    def test_implicit_and_with_explicit_operators(self):
        # Mixed implicit and explicit AND
        result = parse_search_query("python tutorial and django")
        expected = _and(_and(_term("python"), _term("tutorial")), _term("django"))
        self.assertEqual(result, expected)

        # Implicit AND with OR
        result = parse_search_query("python tutorial or java guide")
        expected = _or(
            _and(_term("python"), _term("tutorial")),
            _and(_term("java"), _term("guide")),
        )
        self.assertEqual(result, expected)

    def test_implicit_and_with_not(self):
        # NOT with implicit AND
        result = parse_search_query("not deprecated tutorial")
        expected = _and(_not(_term("deprecated")), _term("tutorial"))
        self.assertEqual(result, expected)

        # Implicit AND with NOT at end
        result = parse_search_query("python tutorial not deprecated")
        expected = _and(
            _and(_term("python"), _term("tutorial")), _not(_term("deprecated"))
        )
        self.assertEqual(result, expected)

    def test_implicit_and_with_parentheses(self):
        # Parentheses with implicit AND
        result = parse_search_query("(python tutorial) or java")
        expected = _or(_and(_term("python"), _term("tutorial")), _term("java"))
        self.assertEqual(result, expected)

        # Complex parentheses with implicit AND
        result = parse_search_query(
            "(machine learning #python) and (web development #javascript)"
        )
        expected = _and(
            _and(_and(_term("machine"), _term("learning")), _tag("python")),
            _and(_and(_term("web"), _term("development")), _tag("javascript")),
        )
        self.assertEqual(result, expected)

    def test_complex_precedence_with_implicit_and(self):
        result = parse_search_query("python tutorial or javascript guide")
        expected = _or(
            _and(_term("python"), _term("tutorial")),
            _and(_term("javascript"), _term("guide")),
        )
        self.assertEqual(result, expected)

        result = parse_search_query(
            "machine learning and (python or r) tutorial #beginner"
        )
        expected = _and(
            _and(
                _and(
                    _and(_term("machine"), _term("learning")),
                    _or(_term("python"), _term("r")),
                ),
                _term("tutorial"),
            ),
            _tag("beginner"),
        )
        self.assertEqual(result, expected)

    def test_operator_words_as_substrings(self):
        # Terms that contain operator words as substrings should be treated as terms
        result = parse_search_query("android and notification")
        expected = _and(_term("android"), _term("notification"))
        self.assertEqual(result, expected)

    def test_complex_queries(self):
        test_cases = [
            (
                "(programming or software) and not client-side and (javascript or python)",
                _and(
                    _and(
                        _or(_term("programming"), _term("software")),
                        _not(_term("client-side")),
                    ),
                    _or(_term("javascript"), _term("python")),
                ),
            ),
            (
                "(machine-learning or ai) and python and not deprecated",
                _and(
                    _and(
                        _or(_term("machine-learning"), _term("ai")),
                        _term("python"),
                    ),
                    _not(_term("deprecated")),
                ),
            ),
            (
                "frontend and (react or vue or angular) and not jquery",
                _and(
                    _and(
                        _term("frontend"),
                        _or(
                            _or(_term("react"), _term("vue")),
                            _term("angular"),
                        ),
                    ),
                    _not(_term("jquery")),
                ),
            ),
            (
                '"machine learning" and (python or r) and not "deep learning"',
                _and(
                    _and(
                        _term("machine learning"),
                        _or(_term("python"), _term("r")),
                    ),
                    _not(_term("deep learning")),
                ),
            ),
            (
                "(#python or #javascript) and tutorial and not #deprecated",
                _and(
                    _and(
                        _or(_tag("python"), _tag("javascript")),
                        _term("tutorial"),
                    ),
                    _not(_tag("deprecated")),
                ),
            ),
            (
                "machine learning tutorial #python beginner",
                _and(
                    _and(
                        _and(
                            _and(_term("machine"), _term("learning")), _term("tutorial")
                        ),
                        _tag("python"),
                    ),
                    _term("beginner"),
                ),
            ),
        ]

        for query, expected_ast in test_cases:
            with self.subTest(query=query):
                result = parse_search_query(query)
                self.assertEqual(result, expected_ast, f"Failed for query: {query}")


class SearchQueryParserErrorTest(TestCase):
    def test_unmatched_left_parenthesis(self):
        with self.assertRaises(SearchQueryParseError) as cm:
            parse_search_query("(programming and books")
        self.assertIn("Expected RPAREN", str(cm.exception))

    def test_unmatched_right_parenthesis(self):
        with self.assertRaises(SearchQueryParseError) as cm:
            parse_search_query("programming and books)")
        self.assertIn("Unexpected token", str(cm.exception))

    def test_empty_parentheses(self):
        with self.assertRaises(SearchQueryParseError) as cm:
            parse_search_query("()")
        self.assertIn("Unexpected token RPAREN", str(cm.exception))

    def test_operator_without_operand(self):
        with self.assertRaises(SearchQueryParseError) as cm:
            parse_search_query("and")
        self.assertIn("Unexpected token AND", str(cm.exception))

    def test_trailing_operator(self):
        with self.assertRaises(SearchQueryParseError) as cm:
            parse_search_query("programming and")
        self.assertIn("Unexpected token EOF", str(cm.exception))

    def test_consecutive_operators(self):
        with self.assertRaises(SearchQueryParseError) as cm:
            parse_search_query("programming and or books")
        self.assertIn("Unexpected token OR", str(cm.exception))

    def test_not_without_operand(self):
        with self.assertRaises(SearchQueryParseError) as cm:
            parse_search_query("not")
        self.assertIn("Unexpected token EOF", str(cm.exception))


class ExpressionToStringTest(TestCase):
    def test_simple_term(self):
        expr = _term("python")
        self.assertEqual(expression_to_string(expr), "python")

    def test_simple_tag(self):
        expr = _tag("python")
        self.assertEqual(expression_to_string(expr), "#python")

    def test_simple_keyword(self):
        expr = _keyword("unread")
        self.assertEqual(expression_to_string(expr), "!unread")

    def test_term_with_spaces(self):
        expr = _term("machine learning")
        self.assertEqual(expression_to_string(expr), '"machine learning"')

    def test_term_with_quotes(self):
        expr = _term('say "hello"')
        self.assertEqual(expression_to_string(expr), '"say \\"hello\\""')

    def test_and_expression_implicit(self):
        expr = _and(_term("python"), _term("tutorial"))
        self.assertEqual(expression_to_string(expr), "python tutorial")

    def test_and_expression_with_tags(self):
        expr = _and(_tag("python"), _tag("django"))
        self.assertEqual(expression_to_string(expr), "#python #django")

    def test_and_expression_complex(self):
        expr = _and(_or(_term("python"), _term("ruby")), _term("tutorial"))
        self.assertEqual(expression_to_string(expr), "(python or ruby) tutorial")

    def test_or_expression(self):
        expr = _or(_term("python"), _term("ruby"))
        self.assertEqual(expression_to_string(expr), "python or ruby")

    def test_or_expression_with_and(self):
        expr = _or(_and(_term("python"), _term("tutorial")), _term("ruby"))
        self.assertEqual(expression_to_string(expr), "python tutorial or ruby")

    def test_not_expression(self):
        expr = _not(_term("deprecated"))
        self.assertEqual(expression_to_string(expr), "not deprecated")

    def test_not_with_tag(self):
        expr = _not(_tag("deprecated"))
        self.assertEqual(expression_to_string(expr), "not #deprecated")

    def test_not_with_and(self):
        expr = _not(_and(_term("python"), _term("deprecated")))
        self.assertEqual(expression_to_string(expr), "not (python deprecated)")

    def test_complex_nested_expression(self):
        expr = _and(
            _or(_term("python"), _term("ruby")),
            _or(_term("tutorial"), _term("guide")),
        )
        result = expression_to_string(expr)
        self.assertEqual(result, "(python or ruby) (tutorial or guide)")

    def test_implicit_and_chain(self):
        expr = _and(_and(_term("machine"), _term("learning")), _term("tutorial"))
        self.assertEqual(expression_to_string(expr), "machine learning tutorial")

    def test_none_expression(self):
        self.assertEqual(expression_to_string(None), "")

    def test_round_trip(self):
        test_cases = [
            "#python",
            "python tutorial",
            "#python #django",
            "python or ruby",
            "not deprecated",
            "(python or ruby) and tutorial",
            "tutorial and (python or ruby)",
            "(python or ruby) tutorial",
            "tutorial (python or ruby)",
        ]

        for query in test_cases:
            with self.subTest(query=query):
                ast = parse_search_query(query)
                result = expression_to_string(ast)
                ast2 = parse_search_query(result)
                self.assertEqual(ast, ast2)


class StripTagFromQueryTest(TestCase):
    def test_single_tag(self):
        result = strip_tag_from_query("#books", "books")
        self.assertEqual(result, "")

    def test_tag_with_and(self):
        result = strip_tag_from_query("#history and #books", "books")
        self.assertEqual(result, "#history")

    def test_tag_with_and_not(self):
        result = strip_tag_from_query("#history and not #books", "books")
        self.assertEqual(result, "#history")

    def test_implicit_and_with_term_and_tags(self):
        result = strip_tag_from_query("roman #history #books", "books")
        self.assertEqual(result, "roman #history")

    def test_tag_in_or_expression(self):
        result = strip_tag_from_query("roman and (#history or #books)", "books")
        self.assertEqual(result, "roman #history")

    def test_complex_or_with_and(self):
        result = strip_tag_from_query(
            "(roman and #books) or (greek and #books)", "books"
        )
        self.assertEqual(result, "roman or greek")

    def test_case_insensitive(self):
        result = strip_tag_from_query("#Books and #History", "books")
        self.assertEqual(result, "#History")

    def test_tag_not_present(self):
        result = strip_tag_from_query("#history and #science", "books")
        self.assertEqual(result, "#history #science")

    def test_multiple_same_tags(self):
        result = strip_tag_from_query("#books or #books", "books")
        self.assertEqual(result, "")

    def test_nested_parentheses(self):
        result = strip_tag_from_query("((#books and tutorial) or guide)", "books")
        self.assertEqual(result, "tutorial or guide")

    def test_not_expression_with_tag(self):
        result = strip_tag_from_query("tutorial and not #books", "books")
        self.assertEqual(result, "tutorial")

    def test_only_not_tag(self):
        result = strip_tag_from_query("not #books", "books")
        self.assertEqual(result, "")

    def test_complex_query(self):
        result = strip_tag_from_query(
            "(#python or #ruby) and tutorial and not #books", "books"
        )
        self.assertEqual(result, "(#python or #ruby) tutorial")

    def test_empty_query(self):
        result = strip_tag_from_query("", "books")
        self.assertEqual(result, "")

    def test_whitespace_only(self):
        result = strip_tag_from_query("   ", "books")
        self.assertEqual(result, "")

    def test_special_keywords_preserved(self):
        result = strip_tag_from_query("!unread and #books", "books")
        self.assertEqual(result, "!unread")

    def test_quoted_terms_preserved(self):
        result = strip_tag_from_query('"machine learning" and #books', "books")
        self.assertEqual(result, '"machine learning"')

    def test_all_tags_in_and_chain(self):
        result = strip_tag_from_query("#books and #books and #books", "books")
        self.assertEqual(result, "")

    def test_tag_similar_name(self):
        # Should not remove #book when removing #books
        result = strip_tag_from_query("#book and #books", "books")
        self.assertEqual(result, "#book")

    def test_invalid_query_returns_original(self):
        # If query is malformed, should return original
        result = strip_tag_from_query("(unclosed paren", "books")
        self.assertEqual(result, "(unclosed paren")

    def test_implicit_and_in_output(self):
        result = strip_tag_from_query("python tutorial #books #django", "books")
        self.assertEqual(result, "python tutorial #django")

    def test_nested_or_simplify_parenthesis(self):
        result = strip_tag_from_query(
            "(#books or tutorial) and (#books or guide)", "books"
        )
        self.assertEqual(result, "tutorial guide")

    def test_nested_or_preserve_parenthesis(self):
        result = strip_tag_from_query(
            "(#books or tutorial or guide) and (#books or help or lesson)", "books"
        )
        self.assertEqual(result, "(tutorial or guide) (help or lesson)")

    def test_left_side_removed(self):
        result = strip_tag_from_query("#books and python", "books")
        self.assertEqual(result, "python")

    def test_right_side_removed(self):
        result = strip_tag_from_query("python and #books", "books")
        self.assertEqual(result, "python")


class StripTagFromQueryLaxSearchTest(TestCase):
    def setUp(self):
        self.lax_profile = type(
            "UserProfile", (), {"tag_search": UserProfile.TAG_SEARCH_LAX}
        )()
        self.strict_profile = type(
            "UserProfile", (), {"tag_search": UserProfile.TAG_SEARCH_STRICT}
        )()

    def test_lax_search_removes_matching_term(self):
        result = strip_tag_from_query("books", "books", self.lax_profile)
        self.assertEqual(result, "")

    def test_lax_search_removes_term_case_insensitive(self):
        result = strip_tag_from_query("Books", "books", self.lax_profile)
        self.assertEqual(result, "")

        result = strip_tag_from_query("BOOKS", "books", self.lax_profile)
        self.assertEqual(result, "")

    def test_lax_search_multiple_terms(self):
        result = strip_tag_from_query("books and history", "books", self.lax_profile)
        self.assertEqual(result, "history")

    def test_lax_search_preserves_non_matching_terms(self):
        result = strip_tag_from_query("history and science", "books", self.lax_profile)
        self.assertEqual(result, "history science")

    def test_lax_search_removes_both_tag_and_term(self):
        result = strip_tag_from_query("books #books", "books", self.lax_profile)
        self.assertEqual(result, "")

    def test_lax_search_mixed_tag_and_term(self):
        result = strip_tag_from_query(
            "books and #history and #books", "books", self.lax_profile
        )
        self.assertEqual(result, "#history")

    def test_lax_search_term_in_or_expression(self):
        result = strip_tag_from_query(
            "(books or history) and guide", "books", self.lax_profile
        )
        self.assertEqual(result, "history guide")

    def test_lax_search_term_in_not_expression(self):
        result = strip_tag_from_query(
            "history and not books", "books", self.lax_profile
        )
        self.assertEqual(result, "history")

    def test_lax_search_only_not_term(self):
        result = strip_tag_from_query("not books", "books", self.lax_profile)
        self.assertEqual(result, "")

    def test_lax_search_complex_query(self):
        result = strip_tag_from_query(
            "(books or #books) and (history or guide)", "books", self.lax_profile
        )
        self.assertEqual(result, "history or guide")

    def test_lax_search_quoted_term_with_same_name(self):
        result = strip_tag_from_query('"books" and history', "books", self.lax_profile)
        self.assertEqual(result, "history")

    def test_lax_search_partial_match_not_removed(self):
        result = strip_tag_from_query("bookshelf", "books", self.lax_profile)
        self.assertEqual(result, "bookshelf")

    def test_lax_search_multiple_occurrences(self):
        result = strip_tag_from_query(
            "books or books or history", "books", self.lax_profile
        )
        self.assertEqual(result, "history")

    def test_lax_search_nested_expressions(self):
        result = strip_tag_from_query(
            "((books and tutorial) or guide) and history", "books", self.lax_profile
        )
        self.assertEqual(result, "(tutorial or guide) history")

    def test_strict_search_preserves_terms(self):
        result = strip_tag_from_query("books", "books", self.strict_profile)
        self.assertEqual(result, "books")

    def test_strict_search_preserves_terms_with_tags(self):
        result = strip_tag_from_query("books #books", "books", self.strict_profile)
        self.assertEqual(result, "books")

    def test_no_profile_defaults_to_strict(self):
        result = strip_tag_from_query("books #books", "books", None)
        self.assertEqual(result, "books")


class ExtractTagNamesFromQueryTest(TestCase):
    def test_empty_query(self):
        result = extract_tag_names_from_query("")
        self.assertEqual(result, [])

    def test_whitespace_query(self):
        result = extract_tag_names_from_query("   ")
        self.assertEqual(result, [])

    def test_single_tag(self):
        result = extract_tag_names_from_query("#python")
        self.assertEqual(result, ["python"])

    def test_multiple_tags(self):
        result = extract_tag_names_from_query("#python and #django")
        self.assertEqual(result, ["django", "python"])

    def test_tags_with_or(self):
        result = extract_tag_names_from_query("#python or #ruby")
        self.assertEqual(result, ["python", "ruby"])

    def test_tags_with_not(self):
        result = extract_tag_names_from_query("not #deprecated")
        self.assertEqual(result, ["deprecated"])

    def test_tags_in_complex_query(self):
        result = extract_tag_names_from_query(
            "(#python or #ruby) and #tutorial and not #deprecated"
        )
        self.assertEqual(result, ["deprecated", "python", "ruby", "tutorial"])

    def test_duplicate_tags(self):
        result = extract_tag_names_from_query("#python and #python")
        self.assertEqual(result, ["python"])

    def test_case_insensitive_deduplication(self):
        result = extract_tag_names_from_query("#Python and #PYTHON and #python")
        self.assertEqual(result, ["python"])

    def test_mixed_tags_and_terms(self):
        result = extract_tag_names_from_query("tutorial #python guide #django")
        self.assertEqual(result, ["django", "python"])

    def test_only_terms_no_tags(self):
        result = extract_tag_names_from_query("tutorial guide")
        self.assertEqual(result, [])

    def test_special_keywords_not_extracted(self):
        result = extract_tag_names_from_query("!unread and #python")
        self.assertEqual(result, ["python"])

    def test_tags_in_nested_parentheses(self):
        result = extract_tag_names_from_query("((#python and #django) or #ruby)")
        self.assertEqual(result, ["django", "python", "ruby"])

    def test_invalid_query_returns_empty(self):
        result = extract_tag_names_from_query("(unclosed paren")
        self.assertEqual(result, [])

    def test_tags_with_hyphens(self):
        result = extract_tag_names_from_query("#machine-learning and #deep-learning")
        self.assertEqual(result, ["deep-learning", "machine-learning"])


class ExtractTagNamesFromQueryLaxSearchTest(TestCase):
    def setUp(self):
        self.lax_profile = type(
            "UserProfile", (), {"tag_search": UserProfile.TAG_SEARCH_LAX}
        )()
        self.strict_profile = type(
            "UserProfile", (), {"tag_search": UserProfile.TAG_SEARCH_STRICT}
        )()

    def test_lax_search_extracts_terms(self):
        result = extract_tag_names_from_query("python and django", self.lax_profile)
        self.assertEqual(result, ["django", "python"])

    def test_lax_search_mixed_tags_and_terms(self):
        result = extract_tag_names_from_query(
            "tutorial #python guide #django", self.lax_profile
        )
        self.assertEqual(result, ["django", "guide", "python", "tutorial"])

    def test_lax_search_deduplicates_tags_and_terms(self):
        result = extract_tag_names_from_query("python #python", self.lax_profile)
        self.assertEqual(result, ["python"])

    def test_lax_search_case_insensitive_dedup(self):
        result = extract_tag_names_from_query("Python #python PYTHON", self.lax_profile)
        self.assertEqual(result, ["python"])

    def test_lax_search_terms_in_or_expression(self):
        result = extract_tag_names_from_query(
            "(python or ruby) and tutorial", self.lax_profile
        )
        self.assertEqual(result, ["python", "ruby", "tutorial"])

    def test_lax_search_terms_in_not_expression(self):
        result = extract_tag_names_from_query(
            "tutorial and not deprecated", self.lax_profile
        )
        self.assertEqual(result, ["deprecated", "tutorial"])

    def test_lax_search_quoted_terms(self):
        result = extract_tag_names_from_query(
            '"machine learning" and #python', self.lax_profile
        )
        self.assertEqual(result, ["machine learning", "python"])

    def test_lax_search_complex_query(self):
        result = extract_tag_names_from_query(
            "(python or #ruby) and tutorial and not #deprecated", self.lax_profile
        )
        self.assertEqual(result, ["deprecated", "python", "ruby", "tutorial"])

    def test_lax_search_special_keywords_not_extracted(self):
        result = extract_tag_names_from_query(
            "!unread and python and #django", self.lax_profile
        )
        self.assertEqual(result, ["django", "python"])

    def test_strict_search_ignores_terms(self):
        result = extract_tag_names_from_query("python and django", self.strict_profile)
        self.assertEqual(result, [])

    def test_strict_search_only_tags(self):
        result = extract_tag_names_from_query(
            "tutorial #python guide #django", self.strict_profile
        )
        self.assertEqual(result, ["django", "python"])

    def test_no_profile_defaults_to_strict(self):
        result = extract_tag_names_from_query("python #django", None)
        self.assertEqual(result, ["django"])
