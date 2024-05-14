import re


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
    l = len(script)
    while i < l:
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
            if i >= l:
                raise ParsingError(script, i, f"Expected an alphabet after colon")
            if not _is_alpha_underline(script[i]):
                raise ParsingError(
                    script, i, f"Expected an alphabet after colon: '{script[i]}'"
                )
            while i < l and _is_alnum_underline(script[i]):
                value += script[i]
                i += 1
            yield Token("tag", value, pos)
            continue

        if script[i] == '"':
            value = ""
            pos = i
            i += 1
            while True:
                if i >= l:
                    raise ParsingError(script, i, 'Expected EOF, expected "')
                if script[i] == "\\":
                    i += 1
                    if i >= l:
                        raise ParsingError(script, i, "Expected EOF")
                    value += script[i]
                    i += 1
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
            while i < l and _is_alnum_underline(script[i]):
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
            f"Unexpected token: {token}, expected type: {'|'.join(expected_types)}",
        )
    if expected_values and token.value not in expected_values:
        raise ParsingError(
            script,
            token.pos,
            f"Unexpected token: {token}, expected value: {'|'.join(expected_values)}",
        )


class Parser:
    KNOWN_FUNCTIONS = {
        "add_tag": [["quoted-string"]],
        "remove_tag": [["quoted-string"]],
        "update_favicon": [],
        "download_thumbnail": [],
    }
    KNOWN_OPERATORS = [":starts_with", ":is", ":contains", ":matches", ":ends_with"]
    KNOWN_KEYS = ["url"]

    def __init__(self, script, tokens):
        self._script = script
        self._tokens = tokens
        self._token = next(self._tokens)

    def _next(self):
        self._token = next(self._tokens)

    def _assert_token(self, expected_types, expected_values=None):
        _assert_token(self._script, self._token, expected_types, expected_values)

    def _parse_condition(self):
        self._assert_token(["identifier"], Parser.KNOWN_KEYS)
        key = self._token
        self._next()
        self._assert_token(["tag"], Parser.KNOWN_OPERATORS)
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
        condition = None
        if type.value != "else":
            condition = self._parse_condition()
        block = self._parse_block()
        else_block = None
        if self._token.value in ["elsif", "else"]:
            else_block = self._parse_if_statement(first_if=False)
        return IfStatement(type, condition, block, else_block)

    def _parse_command(self):
        self._assert_token(["identifier"], Parser.KNOWN_FUNCTIONS.keys())
        command = self._token
        self._next()
        args = []
        for expected_arg in Parser.KNOWN_FUNCTIONS[command.value]:
            self._assert_token(expected_arg)
            args.append(self._token)
            self._next()
        self._assert_token([";"])
        self._next()
        return Command(command, args)

    def _parse_statement(self):
        self._assert_token(["identifier"])

        if self._token.value == "if":
            return self._parse_if_statement()

        return self._parse_command()

    def _parse_program(self):
        statements = []
        while self._token.type != "EOF":
            statements.append(self._parse_statement())
        return Program(statements)

    def parse(self):
        return self._parse_program()


class Evaluator:
    def __init__(self, script, program, context):
        self._script = script
        self._program = program
        self._context = context

    def _evaluate_check(self, check):
        key = check.key.value
        current_value = self._context[key]
        op = check.op.value
        param = check.value.value
        if op == ":starts_with":
            return current_value.lower().startswith(param.lower())
        if op == ":is":
            return current_value.lower() == param.lower()
        if op == ":contains":
            return param.lower() in current_value.lower()
        if op == ":ends_with":
            return current_value.lower().endswith(param.lower())
        if op == ":matches":
            pattern = re.compile(param)
            matches = pattern.match(current_value)
            return matches is not None

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
            self._context["tags"].add(command.args[0].value)
        elif command.command.value == "remove_tag":
            self._assert_args_len(command, 1)
            _assert_token(self._script, command.args[0], ["quoted-string"])
            self._context["tags"].remove(command.args[0].value)
        elif command.command.value == "update_favicon":
            self._assert_args_len(command, 0)
            self._context["should_update_favicon"] = True
        elif command.command.value == "download_thumbnail":
            self._assert_args_len(command, 0)
            self._context["should_download_thumbnail"] = True
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
        res = self.__repr__()
        lines = [
            f"{str(i+1).rjust(5)}. {l}" for i, l in enumerate(self.source.split("\n"))
        ]
        prev_lines = "\n".join(lines[self.line - 3 : self.line - 1])
        cur_line = lines[self.line - 1]
        next_lines = "\n".join(lines[self.line : self.line + 2])
        res += f"\n\n{prev_lines}\n{cur_line}\n here -"
        res += "-" * (self.col - 1)
        res += f"^\n{next_lines}\n"
        return res


def valdate_script(script):
    try:
        parser = Parser(script, _tokenize(script))
        parser.parse()
    except ParsingError as e:
        return ValidationResult(False, e)

    return ValidationResult(True)


if __name__ == "__main__":
    import pprint

    script = """
if url :starts_with "https://www.google.com" {
    add_tag "google";
} elsif url :matches "^.+facebook.+$" {
    add_tag "facebook";
    remove_tag "video";
}

update_favicon;
download_thumbnail;
""".lstrip()

    print(script)

    valid = valdate_script(script)
    print(valid)
    print()

    for token in _tokenize(script):
        print(token.dump(script))
    print()

    parser = Parser(script, _tokenize(script))
    program = parser.parse()
    print(program.dump(script))
    print()

    context = {
        "url": "https://www.facebook.com",
        "tags": set(["video"]),
        "should_update_favicon": False,
        "should_download_thumbnail": False,
    }
    e = Evaluator(
        script,
        program,
        context,
    )
    e.evaluate()
    pprint.pp(context)
