script = """
if url :starts_with "https://www.google.com" {
    add_tag "google";
} elsif url :starts_with "https://www.facebook.com" {
    add_tag "facebook";
}

update_favicon;
download_thumbnail;
"""


def is_alpha_underline(c: str):
    return c.isalpha() or c == "_"


def is_alnum_underline(c: str):
    return c.isalnum() or c == "_"


class Token:
    def __init__(self, type, value, pos):
        self.type = type
        self.value = value
        self.pos = pos

    def __repr__(self):
        return f"Token({self.type}, {self.value}, {self.pos})"


def _tokenize(script: str):
    i = 0
    while i < len(script):
        if script[i].isspace():
            i += 1
            continue

        if script[i] in ["{", "}", "(", ")", ";"]:
            yield Token(script[i], script[i], i)
            i += 1
            continue

        if script[i] == ":":
            value = ":"
            pos = i
            i += 1
            if not is_alpha_underline(script[i]):
                raise ValueError(
                    f"Expected an alphabet after colon: {script[i]}, pos: {i}"
                )
            while is_alnum_underline(script[i]):
                value += script[i]
                i += 1
            yield Token("tag", value, pos)
            continue

        if script[i] == '"':
            value = ""
            pos = i
            i += 1
            while True:
                if script[i] == "\\" and script[i + 1] == '"':
                    value += '"'
                    i += 2
                    continue
                if script[i] == "\\" and script[i + 1] == "\\":
                    value += "\\"
                    i += 2
                    continue
                if script[i] == '"':
                    i += 1
                    break
                value += script[i]
                i += 1
            yield Token("quoted-string", value, pos)
            continue

        if is_alpha_underline(script[i]):
            value = script[i]
            pos = i
            i += 1
            while is_alnum_underline(script[i]):
                value += script[i]
                i += 1
            yield Token("identifier", value, pos)
            continue

        raise ValueError(f"Unexpected character: {script[i]}, pos: {i}")

    yield Token("EOF", "", i)


class Program:
    def __init__(self, statements):
        self.statements = statements

    def __repr__(self):
        return f"Program({self.statements})"


class IfStatement:
    def __init__(self, type, condition, block, else_block):
        self.type = type
        self.condition = condition
        self.block = block
        self.else_block = else_block

    def __repr__(self):
        return f"IfStatement({self.condition}, {self.block}, {self.else_block})"


class Check:
    def __init__(self, key, op, value):
        self.key = key
        self.op = op
        self.value = value

    def __repr__(self):
        return f"Check({self.key}, {self.op}, {self.value})"


class Command:
    def __init__(self, command, args):
        self.command = command
        self.args = args

    def __repr__(self):
        return f"Command({self.command}, {self.args})"


def _assert_token(token, expected_types, expected_values=None):
    if token.type not in expected_types:
        raise ValueError(f"Unexpected token: {token}, expected: {expected_types}")
    if expected_values:
        if token.value not in expected_values:
            raise ValueError(f"Unexpected token: {token}, expected: {expected_values}")


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0
        self._token = next(self.tokens)

    def _next(self):
        self.i += 1
        self._token = next(self.tokens)

    def _assert_token(self, expected_types, expected_values=None):
        _assert_token(self._token, expected_types, expected_values)

    def _parse_condition(self):
        self._assert_token(["identifier"])
        key = self._token
        self._next()
        self._assert_token(["tag"])
        op = self._token
        self._next()
        self._assert_token(["quoted-string"])
        value = self._token
        self._next()
        return Check(key, op, value)

    def _parse_block(self):
        self._assert_token(["{"])
        self._next()
        statements = []
        while self._token.value != "}":
            statements.append(self._parse_statement())
        self._next()
        return Program(statements)

    def _parse_if_statement(self, first_if=True):
        expected_values = ["if"] if first_if else ["elsif", "else"]
        self._assert_token(["identifier"], expected_values)
        type = self._token
        self._next()
        condition = self._parse_condition() if type.value != "else" else None
        block = self._parse_block()
        else_block = None
        if self._token.value in ["elsif", "else"]:
            else_block = self._parse_if_statement(first_if=False)
        return IfStatement(type, condition, block, else_block)

    def _parse_command(self):
        self._assert_token(["identifier"])
        command = self._token
        self._next()
        args = []
        while self._token.value != ";":
            self._assert_token(["quoted-string"])
            args.append(self._token)
            self._next()
        self._next()
        return Command(command, args)

    def _parse_statement(self):
        if self._token.type == "identifier" and self._token.value == "if":
            return self._parse_if_statement()

        if self._token.type == "identifier":
            return self._parse_command()

        raise ValueError(f"Unexpected token: {self._token}")

    def _parse_program(self):
        statements = []
        while True:
            if self._token.type == "EOF":
                break
            statements.append(self._parse_statement())
        return Program(statements)

    def parse(self):
        return self._parse_program()


class Evaluator:
    def __init__(self, program, obj):
        self._program = program
        self._obj = obj
        self.tags = set()
        self.should_update_favicon = False
        self.should_download_thumbnail = False

    def _evaluate_check(self, check):
        key = check.key.value
        op = check.op.value
        value = check.value.value
        if op == ":starts_with":
            return self._obj[key].startswith(value.lower())
        raise ValueError(f"Unknown operator: {op}")

    def _evaluate_if_statement(self, if_statement):
        ok = if_statement.condition is None or self._evaluate_check(
            if_statement.condition
        )
        if ok:
            self._evaluate_program(if_statement.block)
        elif if_statement.else_block:
            self._evaluate_if_statement(if_statement.else_block)

    def _evaluate_command(self, command):
        if command.command.value == "add_tag":
            if len(command.args) != 1:
                raise ValueError(
                    f"Expected 1 argument, got {len(command.args)}, pos: {command.command.pos}"
                )
            _assert_token(command.args[0], ["quoted-string"])
            self.tags.add(command.args[0].value)
        elif command.command.value == "update_favicon":
            self.should_update_favicon = True
        elif command.command.value == "download_thumbnail":
            self.should_download_thumbnail = True
        else:
            raise ValueError(f"Unknown command: {command.command.value}")

    def _evaluate_program(self, program):
        for statement in program.statements:
            if isinstance(statement, IfStatement):
                self._evaluate_if_statement(statement)
            elif isinstance(statement, Command):
                self._evaluate_command(statement)
            else:
                raise ValueError(f"Unknown statement: {statement}")

    def evaluate(self):
        self._evaluate_program(self._program)


parser = Parser(_tokenize(script))
program = parser.parse()
print(program)
e = Evaluator(program, {"url": "https://www.facebook.com"})
e.evaluate()
print(
    {
        "tags": e.tags,
        "should_update_favicon": e.should_update_favicon,
        "should_download_thumbnail": e.should_download_thumbnail,
    }
)
