from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from bookmarks.models import UserProfile


class TokenType(Enum):
    TERM = "TERM"
    TAG = "TAG"
    SPECIAL_KEYWORD = "SPECIAL_KEYWORD"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    EOF = "EOF"


@dataclass
class Token:
    type: TokenType
    value: str
    position: int


class SearchQueryTokenizer:
    def __init__(self, query: str):
        self.query = query.strip()
        self.position = 0
        self.current_char = self.query[0] if self.query else None

    def advance(self):
        """Move to the next character in the query."""
        self.position += 1
        if self.position >= len(self.query):
            self.current_char = None
        else:
            self.current_char = self.query[self.position]

    def skip_whitespace(self):
        """Skip whitespace characters."""
        while self.current_char and self.current_char.isspace():
            self.advance()

    def read_term(self) -> str:
        """Read a search term (sequence of non-whitespace, non-special characters)."""
        term = ""

        while (
            self.current_char
            and not self.current_char.isspace()
            and self.current_char not in "()\"'#!"
        ):
            term += self.current_char
            self.advance()

        return term

    def read_quoted_string(self, quote_char: str) -> str:
        """Read a quoted string, handling escaped quotes."""
        content = ""
        self.advance()  # skip opening quote

        while self.current_char and self.current_char != quote_char:
            if self.current_char == "\\":
                # Handle escaped characters
                self.advance()
                if self.current_char:
                    if self.current_char == "n":
                        content += "\n"
                    elif self.current_char == "t":
                        content += "\t"
                    elif self.current_char == "r":
                        content += "\r"
                    elif self.current_char == "\\":
                        content += "\\"
                    elif self.current_char == quote_char:
                        content += quote_char
                    else:
                        # For any other escaped character, just include it as-is
                        content += self.current_char
                    self.advance()
            else:
                content += self.current_char
                self.advance()

        if self.current_char == quote_char:
            self.advance()  # skip closing quote
        else:
            # Unclosed quote - we could raise an error here, but let's be lenient
            # and treat it as if the quote was closed at the end
            pass

        return content

    def read_tag(self) -> str:
        """Read a tag (starts with # and continues until whitespace or special chars)."""
        tag = ""
        self.advance()  # skip the # character

        while (
            self.current_char
            and not self.current_char.isspace()
            and self.current_char not in "()\"'"
        ):
            tag += self.current_char
            self.advance()

        return tag

    def read_special_keyword(self) -> str:
        """Read a special keyword (starts with ! and continues until whitespace or special chars)."""
        keyword = ""
        self.advance()  # skip the ! character

        while (
            self.current_char
            and not self.current_char.isspace()
            and self.current_char not in "()\"'"
        ):
            keyword += self.current_char
            self.advance()

        return keyword

    def tokenize(self) -> List[Token]:
        """Convert the query string into a list of tokens."""
        tokens = []

        while self.current_char:
            self.skip_whitespace()

            if not self.current_char:
                break

            start_pos = self.position

            if self.current_char == "(":
                tokens.append(Token(TokenType.LPAREN, "(", start_pos))
                self.advance()
            elif self.current_char == ")":
                tokens.append(Token(TokenType.RPAREN, ")", start_pos))
                self.advance()
            elif self.current_char in "\"'":
                # Read a quoted string - always treated as a term
                quote_char = self.current_char
                term = self.read_quoted_string(quote_char)
                tokens.append(Token(TokenType.TERM, term, start_pos))
            elif self.current_char == "#":
                # Read a tag
                tag = self.read_tag()
                # Only add the tag token if it has content
                if tag:
                    tokens.append(Token(TokenType.TAG, tag, start_pos))
            elif self.current_char == "!":
                # Read a special keyword
                keyword = self.read_special_keyword()
                # Only add the keyword token if it has content
                if keyword:
                    tokens.append(Token(TokenType.SPECIAL_KEYWORD, keyword, start_pos))
            else:
                # Read a term and check if it's an operator
                term = self.read_term()
                term_lower = term.lower()

                if term_lower == "and":
                    tokens.append(Token(TokenType.AND, term, start_pos))
                elif term_lower == "or":
                    tokens.append(Token(TokenType.OR, term, start_pos))
                elif term_lower == "not":
                    tokens.append(Token(TokenType.NOT, term, start_pos))
                else:
                    tokens.append(Token(TokenType.TERM, term, start_pos))

        tokens.append(Token(TokenType.EOF, "", len(self.query)))
        return tokens


class SearchExpression:
    pass


@dataclass
class TermExpression(SearchExpression):
    term: str


@dataclass
class TagExpression(SearchExpression):
    tag: str


@dataclass
class SpecialKeywordExpression(SearchExpression):
    keyword: str


@dataclass
class AndExpression(SearchExpression):
    left: SearchExpression
    right: SearchExpression


@dataclass
class OrExpression(SearchExpression):
    left: SearchExpression
    right: SearchExpression


@dataclass
class NotExpression(SearchExpression):
    operand: SearchExpression


class SearchQueryParseError(Exception):
    def __init__(self, message: str, position: int):
        self.message = message
        self.position = position
        super().__init__(f"{message} at position {position}")


class SearchQueryParser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.position = 0
        self.current_token = tokens[0] if tokens else Token(TokenType.EOF, "", 0)

    def advance(self):
        """Move to the next token."""
        if self.position < len(self.tokens) - 1:
            self.position += 1
            self.current_token = self.tokens[self.position]

    def consume(self, expected_type: TokenType) -> Token:
        """Consume a token of the expected type or raise an error."""
        if self.current_token.type == expected_type:
            token = self.current_token
            self.advance()
            return token
        else:
            raise SearchQueryParseError(
                f"Expected {expected_type.value}, got {self.current_token.type.value}",
                self.current_token.position,
            )

    def parse(self) -> Optional[SearchExpression]:
        """Parse the tokens into an AST."""
        if not self.tokens or (
            len(self.tokens) == 1 and self.tokens[0].type == TokenType.EOF
        ):
            return None

        expr = self.parse_or_expression()

        if self.current_token.type != TokenType.EOF:
            raise SearchQueryParseError(
                f"Unexpected token {self.current_token.type.value}",
                self.current_token.position,
            )

        return expr

    def parse_or_expression(self) -> SearchExpression:
        """Parse OR expressions (lowest precedence)."""
        left = self.parse_and_expression()

        while self.current_token.type == TokenType.OR:
            self.advance()  # consume OR
            right = self.parse_and_expression()
            left = OrExpression(left, right)

        return left

    def parse_and_expression(self) -> SearchExpression:
        """Parse AND expressions (medium precedence), including implicit AND."""
        left = self.parse_not_expression()

        while self.current_token.type == TokenType.AND or self.current_token.type in [
            TokenType.TERM,
            TokenType.TAG,
            TokenType.SPECIAL_KEYWORD,
            TokenType.LPAREN,
            TokenType.NOT,
        ]:

            if self.current_token.type == TokenType.AND:
                self.advance()  # consume explicit AND
            # else: implicit AND (don't advance token)

            right = self.parse_not_expression()
            left = AndExpression(left, right)

        return left

    def parse_not_expression(self) -> SearchExpression:
        """Parse NOT expressions (high precedence)."""
        if self.current_token.type == TokenType.NOT:
            self.advance()  # consume NOT
            operand = self.parse_not_expression()  # right associative
            return NotExpression(operand)

        return self.parse_primary_expression()

    def parse_primary_expression(self) -> SearchExpression:
        """Parse primary expressions (terms, tags, special keywords, and parenthesized expressions)."""
        if self.current_token.type == TokenType.TERM:
            term = self.current_token.value
            self.advance()
            return TermExpression(term)
        elif self.current_token.type == TokenType.TAG:
            tag = self.current_token.value
            self.advance()
            return TagExpression(tag)
        elif self.current_token.type == TokenType.SPECIAL_KEYWORD:
            keyword = self.current_token.value
            self.advance()
            return SpecialKeywordExpression(keyword)
        elif self.current_token.type == TokenType.LPAREN:
            self.advance()  # consume (
            expr = self.parse_or_expression()
            self.consume(TokenType.RPAREN)  # consume )
            return expr
        else:
            raise SearchQueryParseError(
                f"Unexpected token {self.current_token.type.value}",
                self.current_token.position,
            )


def parse_search_query(query: str) -> Optional[SearchExpression]:
    if not query or not query.strip():
        return None

    tokenizer = SearchQueryTokenizer(query)
    tokens = tokenizer.tokenize()
    parser = SearchQueryParser(tokens)
    return parser.parse()


def _needs_parentheses(expr: SearchExpression, parent_type: type) -> bool:
    if isinstance(expr, OrExpression) and parent_type == AndExpression:
        return True
    # AndExpression or OrExpression needs parentheses when inside NotExpression
    if isinstance(expr, (AndExpression, OrExpression)) and parent_type == NotExpression:
        return True
    return False


def _is_simple_expression(expr: SearchExpression) -> bool:
    """Check if an expression is simple (term, tag, or keyword)."""
    return isinstance(expr, (TermExpression, TagExpression, SpecialKeywordExpression))


def _expression_to_string(expr: SearchExpression, parent_type: type = None) -> str:
    if isinstance(expr, TermExpression):
        # Quote terms if they contain spaces or special characters
        if " " in expr.term or any(c in expr.term for c in ["(", ")", '"', "'"]):
            # Escape any quotes in the term
            escaped = expr.term.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        return expr.term

    elif isinstance(expr, TagExpression):
        return f"#{expr.tag}"

    elif isinstance(expr, SpecialKeywordExpression):
        return f"!{expr.keyword}"

    elif isinstance(expr, NotExpression):
        # Don't pass parent type to children
        operand_str = _expression_to_string(expr.operand, None)
        # Add parentheses if the operand is a binary operation
        if isinstance(expr.operand, (AndExpression, OrExpression)):
            return f"not ({operand_str})"
        return f"not {operand_str}"

    elif isinstance(expr, AndExpression):
        # Don't pass parent type to children - they'll add their own parens only if needed
        left_str = _expression_to_string(expr.left, None)
        right_str = _expression_to_string(expr.right, None)

        # Add parentheses to children if needed for precedence
        if _needs_parentheses(expr.left, AndExpression):
            left_str = f"({left_str})"
        if _needs_parentheses(expr.right, AndExpression):
            right_str = f"({right_str})"

        result = f"{left_str} {right_str}"

        # Add outer parentheses if needed based on parent context
        if parent_type and _needs_parentheses(expr, parent_type):
            result = f"({result})"

        return result

    elif isinstance(expr, OrExpression):
        # Don't pass parent type to children
        left_str = _expression_to_string(expr.left, None)
        right_str = _expression_to_string(expr.right, None)

        # OrExpression children don't need parentheses unless they're also OR (handled by recursion)
        result = f"{left_str} or {right_str}"

        # Add outer parentheses if needed based on parent context
        if parent_type and _needs_parentheses(expr, parent_type):
            result = f"({result})"

        return result

    else:
        raise ValueError(f"Unknown expression type: {type(expr)}")


def expression_to_string(expr: Optional[SearchExpression]) -> str:
    if expr is None:
        return ""
    return _expression_to_string(expr)


def _strip_tag_from_expression(
    expr: Optional[SearchExpression], tag_name: str, enable_lax_search: bool = False
) -> Optional[SearchExpression]:
    if expr is None:
        return None

    if isinstance(expr, TagExpression):
        # Remove this tag if it matches
        if expr.tag.lower() == tag_name.lower():
            return None
        return expr

    elif isinstance(expr, TermExpression):
        # In lax search mode, also remove terms that match the tag name
        if enable_lax_search and expr.term.lower() == tag_name.lower():
            return None
        return expr

    elif isinstance(expr, SpecialKeywordExpression):
        # Keep special keywords as-is
        return expr

    elif isinstance(expr, NotExpression):
        # Recursively filter the operand
        filtered_operand = _strip_tag_from_expression(
            expr.operand, tag_name, enable_lax_search
        )
        if filtered_operand is None:
            # If the operand is removed, the whole NOT expression should be removed
            return None
        return NotExpression(filtered_operand)

    elif isinstance(expr, AndExpression):
        # Recursively filter both sides
        left = _strip_tag_from_expression(expr.left, tag_name, enable_lax_search)
        right = _strip_tag_from_expression(expr.right, tag_name, enable_lax_search)

        # If both sides are removed, remove the AND expression
        if left is None and right is None:
            return None
        # If one side is removed, return the other side
        elif left is None:
            return right
        elif right is None:
            return left
        else:
            return AndExpression(left, right)

    elif isinstance(expr, OrExpression):
        # Recursively filter both sides
        left = _strip_tag_from_expression(expr.left, tag_name, enable_lax_search)
        right = _strip_tag_from_expression(expr.right, tag_name, enable_lax_search)

        # If both sides are removed, remove the OR expression
        if left is None and right is None:
            return None
        # If one side is removed, return the other side
        elif left is None:
            return right
        elif right is None:
            return left
        else:
            return OrExpression(left, right)

    else:
        # Unknown expression type, return as-is
        return expr


def strip_tag_from_query(
    query: str, tag_name: str, user_profile: UserProfile | None = None
) -> str:
    try:
        ast = parse_search_query(query)
    except SearchQueryParseError:
        return query

    if ast is None:
        return ""

    # Determine if lax search is enabled
    enable_lax_search = False
    if user_profile is not None:
        enable_lax_search = user_profile.tag_search == UserProfile.TAG_SEARCH_LAX

    # Strip the tag from the AST
    filtered_ast = _strip_tag_from_expression(ast, tag_name, enable_lax_search)

    # Convert back to a query string
    return expression_to_string(filtered_ast)


def _extract_tag_names_from_expression(
    expr: Optional[SearchExpression], enable_lax_search: bool = False
) -> List[str]:
    if expr is None:
        return []

    if isinstance(expr, TagExpression):
        return [expr.tag]

    elif isinstance(expr, TermExpression):
        # In lax search mode, terms are also considered tags
        if enable_lax_search:
            return [expr.term]
        return []

    elif isinstance(expr, SpecialKeywordExpression):
        # Special keywords are not tags
        return []

    elif isinstance(expr, NotExpression):
        # Recursively extract from the operand
        return _extract_tag_names_from_expression(expr.operand, enable_lax_search)

    elif isinstance(expr, (AndExpression, OrExpression)):
        # Recursively extract from both sides and combine
        left_tags = _extract_tag_names_from_expression(expr.left, enable_lax_search)
        right_tags = _extract_tag_names_from_expression(expr.right, enable_lax_search)
        return left_tags + right_tags

    else:
        # Unknown expression type
        return []


def extract_tag_names_from_query(
    query: str, user_profile: UserProfile | None = None
) -> List[str]:
    try:
        ast = parse_search_query(query)
    except SearchQueryParseError:
        return []

    if ast is None:
        return []

    # Determine if lax search is enabled
    enable_lax_search = False
    if user_profile is not None:
        enable_lax_search = user_profile.tag_search == UserProfile.TAG_SEARCH_LAX

    # Extract tag names from the AST
    tag_names = _extract_tag_names_from_expression(ast, enable_lax_search)

    # Deduplicate (case-insensitive) and sort
    seen = set()
    unique_tags = []
    for tag in tag_names:
        tag_lower = tag.lower()
        if tag_lower not in seen:
            seen.add(tag_lower)
            unique_tags.append(tag_lower)

    return sorted(unique_tags)
