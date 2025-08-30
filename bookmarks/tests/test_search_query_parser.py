from django.test import TestCase

from bookmarks.services.search_query_parser import (
    SearchQueryTokenizer,
    TokenType,
    SearchExpression,
    TermExpression,
    TagExpression,
    AndExpression,
    OrExpression,
    NotExpression,
    SearchQueryParseError,
    parse_search_query,
)


def _term(term: str) -> TermExpression:
    """Helper to create a TermExpression."""
    return TermExpression(term)


def _tag(tag: str) -> TagExpression:
    """Helper to create a TagExpression."""
    return TagExpression(tag)


def _and(left: SearchExpression, right: SearchExpression) -> AndExpression:
    """Helper to create an AndExpression."""
    return AndExpression(left, right)


def _or(left: SearchExpression, right: SearchExpression) -> OrExpression:
    """Helper to create an OrExpression."""
    return OrExpression(left, right)


def _not(operand: SearchExpression) -> NotExpression:
    """Helper to create a NotExpression."""
    return NotExpression(operand)


class SearchQueryTokenizerTest(TestCase):
    """Test cases for the search query tokenizer."""

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
        # Tag with just # should be handled gracefully
        tokenizer = SearchQueryTokenizer("# ")
        tokens = tokenizer.tokenize()
        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[0].type, TokenType.TAG)
        self.assertEqual(tokens[0].value, "")
        self.assertEqual(tokens[1].type, TokenType.EOF)


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
        # "not not a" should parse as "not (not a)" (right associative)
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
        # "programming and (books or streaming) and not client-side"
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
        # Test that operators work in different cases
        result = parse_search_query("programming AND books OR streaming")
        # Should parse as: (programming AND books) OR streaming
        expected = _or(_and(_term("programming"), _term("books")), _term("streaming"))
        self.assertEqual(result, expected)

        # Test malformed query with missing operator between terms and NOT
        with self.assertRaises(SearchQueryParseError):
            parse_search_query("programming AND books OR streaming NOT videos")

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

    def test_operator_words_as_substrings(self):
        # Terms that contain operator words as substrings should be treated as terms
        result = parse_search_query("android and notification")
        expected = _and(_term("android"), _term("notification"))
        self.assertEqual(result, expected)

    def test_deeply_nested_parentheses(self):
        result = parse_search_query("(((programming)))")
        expected = _term("programming")
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
        ]

        for query, expected_ast in test_cases:
            with self.subTest(query=query):
                result = parse_search_query(query)
                self.assertEqual(result, expected_ast, f"Failed for query: {query}")


class SearchQueryParserErrorTest(TestCase):
    """Test cases for parser error handling."""

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
