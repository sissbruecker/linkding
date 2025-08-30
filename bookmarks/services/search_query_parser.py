from dataclasses import dataclass
from enum import Enum
from typing import List, Union, Optional


class TokenType(Enum):
    TERM = "TERM"
    TAG = "TAG"
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
    """Tokenizer for the search query language."""

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
        start_pos = self.position
        term = ""

        while (
            self.current_char
            and not self.current_char.isspace()
            and self.current_char not in "()\"'#"
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
            else:
                # Read a term and check if it's a keyword
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


# AST Node classes for different expression types


class SearchExpression:
    """Base class for all search expressions."""

    pass


@dataclass
class TermExpression(SearchExpression):
    """A search term expression."""

    term: str


@dataclass
class TagExpression(SearchExpression):
    """A tag expression (starts with #)."""

    tag: str


@dataclass
class AndExpression(SearchExpression):
    """A logical AND expression."""

    left: SearchExpression
    right: SearchExpression


@dataclass
class OrExpression(SearchExpression):
    """A logical OR expression."""

    left: SearchExpression
    right: SearchExpression


@dataclass
class NotExpression(SearchExpression):
    """A logical NOT expression."""

    operand: SearchExpression


class SearchQueryParseError(Exception):
    """Exception raised when parsing fails."""

    def __init__(self, message: str, position: int):
        self.message = message
        self.position = position
        super().__init__(f"{message} at position {position}")


class SearchQueryParser:
    """Parser for the search query language using recursive descent parsing."""

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
        """Parse AND expressions (medium precedence)."""
        left = self.parse_not_expression()

        while self.current_token.type == TokenType.AND:
            self.advance()  # consume AND
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
        """Parse primary expressions (terms, tags, and parenthesized expressions)."""
        if self.current_token.type == TokenType.TERM:
            term = self.current_token.value
            self.advance()
            return TermExpression(term)
        elif self.current_token.type == TokenType.TAG:
            tag = self.current_token.value
            self.advance()
            return TagExpression(tag)
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
    """Parse a search query string into an AST.

    Args:
        query: The search query string to parse

    Returns:
        The parsed AST or None if the query is empty

    Raises:
        SearchQueryParseError: If the query is malformed
    """
    if not query or not query.strip():
        return None

    tokenizer = SearchQueryTokenizer(query)
    tokens = tokenizer.tokenize()
    parser = SearchQueryParser(tokens)
    return parser.parse()
