script = """
if url :starts_with "https://www.google.com" {
    add_tag "google";
} elsif url :starts_with "https://www.facebook.com" {
    add_tag "facebook";
}

update_favicon;
download_thumbnail;
"""


def _is_alpha_underline(c: str):
    return c.isalpha() or c == "_"


def _is_alnum_underline(c: str):
    return c.isalnum() or c == "_"


def _pos_to_line_col(script: str, pos: int):
    line = 1
    col = 1
    for i in range(pos):
        if script[i] == "\n":
            line += 1
            col = 1
        else:
            col += 1
    return line, col


def _pos_str(script, pos):
    line, col = _pos_to_line_col(script, pos)
    return f"at line {line}, col {col}"


class Token:
    def __init__(self, type, value, pos):
        self.type = type
        self.value = value
        self.pos = pos

    def __repr__(self):
        return f"Token({self.type}, {self.value})"

    def dump(self, script):
        value = self.value
        if self.type == "quoted-string":
            if len(value) > 23:
                value = value[:20] + "..."
            value = f'"{value}"'
        return f"Token({self.type}, {value}) {_pos_str(script, self.pos)}"


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
            if not _is_alpha_underline(script[i]):
                raise ParsingError(
                    script, i, f"Expected an alphabet after colon: '{script[i]}'"
                )
            while _is_alnum_underline(script[i]):
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

        if _is_alpha_underline(script[i]):
            value = script[i]
            pos = i
            i += 1
            while _is_alnum_underline(script[i]):
                value += script[i]
                i += 1
            yield Token("identifier", value, pos)
            continue

        raise ParsingError(script, i, f"Unexpected character: '{script[i]}'")

    yield Token("EOF", "", i)


class Program:
    def __init__(self, statements):
        self.statements = statements

    def __repr__(self):
        return f"Program({self.statements})"

    def dump(self, script, indent=""):
        res = f"Program(\n"
        res += f"{indent}  statements=["
        for i, statement in enumerate(self.statements):
            if i > 0:
                res += ","
            s = statement.dump(script, indent + "    ")
            res += f"\n{indent}    {s}"
        if len(self.statements) > 0:
            res += f"\n{indent}  "
        res += "]\n"
        res += f"{indent})"
        return res


class IfStatement:
    def __init__(self, type, condition, block, else_block):
        self.type = type
        self.condition = condition
        self.block = block
        self.else_block = else_block

    def __repr__(self):
        return f"IfStatement({self.condition}, {self.block}, {self.else_block})"

    def dump(self, script, indent=""):
        res = f"IfStatement(\n"
        res += f"{indent}  type={self.type.dump(script)}\n"
        if self.condition:
            condition = self.condition.dump(script, indent + "  ")
            res += f"{indent}  condition={condition}\n"
        ok = self.block.dump(script, indent + "  ")
        res += f"{indent}  ok={ok}\n"
        if self.else_block:
            else_block = self.else_block.dump(script, indent + "  ")
            res += f"{indent}  else_block={else_block}\n"
        res += f"{indent})"
        return res


class Check:
    def __init__(self, key, op, value):
        self.key = key
        self.op = op
        self.value = value

    def __repr__(self):
        return f"Check({self.key}, {self.op}, {self.value})"

    def dump(self, script, indent=""):
        res = f"Check(\n"
        res += f"{indent}  key={self.key.dump(script)}\n"
        res += f"{indent}  op={self.op.dump(script)}\n"
        res += f"{indent}  value={self.value.dump(script)}\n"
        res += f"{indent})"
        return res


class Command:
    def __init__(self, command, args):
        self.command = command
        self.args = args

    def __repr__(self):
        return f"Command({self.command}, {self.args})"

    def dump(self, script, indent=""):
        res = f"Command(\n"
        res += f"{indent}  command={self.command.dump(script)}\n"
        res += f"{indent}  args=["
        for i, arg in enumerate(self.args):
            if i > 0:
                res += ", "
            res += f"\n{indent}    {arg.dump(script)}"
        if len(self.args) > 0:
            res += f"\n{indent}  "
        res += "]\n"
        res += f"{indent})"
        return res


def _assert_token(script, token, expected_types, expected_values=None):
    if token.type not in expected_types:
        raise ParsingError(
            script,
            token.pos,
            f"Unexpected token: {token}, expected: {'|'.join(expected_types)}",
        )
    if expected_values:
        if token.value not in expected_values:
            raise ParsingError(
                script,
                token.pos,
                f"Unexpected token: {token}, expected: {'|'.join(expected_values)}",
            )


class Parser:
    def __init__(self, script, tokens):
        self._script = script
        self._tokens = tokens
        self._token = next(self._tokens)

    def _next(self):
        self._token = next(self._tokens)

    def _assert_token(self, expected_types, expected_values=None):
        _assert_token(self._script, self._token, expected_types, expected_values)

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
        self._assert_token(["identifier"])

        if self._token.value == "if":
            return self._parse_if_statement()

        return self._parse_command()

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
    def __init__(self, script, program, obj):
        self._script = script
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
        raise ParsingError(self._script, check.op.pos, f"Unknown operator: {op}")

    def _evaluate_if_statement(self, if_statement):
        ok = if_statement.condition is None or self._evaluate_check(
            if_statement.condition
        )
        if ok:
            self._evaluate_program(if_statement.block)
        elif if_statement.else_block:
            self._evaluate_if_statement(if_statement.else_block)

    def _assert_args_len(self, command, expected_len):
        if len(command.args) != expected_len:
            raise ParsingError(
                self._script,
                command.command.pos,
                f"Expected {expected_len} arguments, got {len(command.args)}",
            )

    def _evaluate_command(self, command):
        if command.command.value == "add_tag":
            self._assert_args_len(command, 1)
            _assert_token(self._script, command.args[0], ["quoted-string"])
            self.tags.add(command.args[0].value)
        elif command.command.value == "update_favicon":
            self._assert_args_len(command, 0)
            self.should_update_favicon = True
        elif command.command.value == "download_thumbnail":
            self._assert_args_len(command, 0)
            self.should_download_thumbnail = True
        else:
            raise ParsingError(
                self._script,
                command.command.pos,
                f"Unknown command: {command.command.value}",
            )

    def _evaluate_program(self, program):
        for statement in program.statements:
            if isinstance(statement, IfStatement):
                self._evaluate_if_statement(statement)
            elif isinstance(statement, Command):
                self._evaluate_command(statement)
            else:
                raise ParsingError(
                    self._script, statement.pos, f"Unknown statement: {statement}"
                )

    def evaluate(self):
        self._evaluate_program(self._program)


class ValidationResult:
    def __init__(self, valid, error=None):
        self.valid = valid
        self.error = error

    def __repr__(self):
        return f"ValidationResult(valid={self.valid}, error={self.error})"


class ParsingError(ValueError):
    def __init__(self, source, pos, msg) -> None:
        line, col = _pos_to_line_col(script, pos)
        msg += f" {_pos_str(source, pos)}"
        super().__init__(msg)
        self.source = source
        self.pos = pos
        self.line = line
        self.col = col

    def __str__(self):
        return self.__repr__()


def valdate_script(script):
    try:
        parser = Parser(script, _tokenize(script))
        parser.parse()
    except ParsingError as e:
        return ValidationResult(False, e)

    return ValidationResult(True)


print(script)
print()

valid = valdate_script(script)
print(valid)
print()

for token in _tokenize(script):
    print(token)
print()

parser = Parser(script, _tokenize(script))
program = parser.parse()
print(program.dump(script))
print()

e = Evaluator(script, program, {"url": "https://www.facebook.com"})
e.evaluate()
print(
    {
        "tags": e.tags,
        "should_update_favicon": e.should_update_favicon,
        "should_download_thumbnail": e.should_download_thumbnail,
    }
)
