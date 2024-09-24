from urllib.parse import urlparse, parse_qs
import re
import idna


def get_tags(script: str, url: str):
    parsed_url = urlparse(url.lower())
    result = set()

    if not parsed_url.hostname:
        return result

    for line in script.lower().split("\n"):
        if "#" in line:
            i = line.index("#")
            line = line[:i]

        parts = line.split()
        if len(parts) < 2:
            continue

        # to parse a host name from the pattern URL, ensure it has a scheme
        pattern_url = "//" + re.sub("^https?://", "", parts[0])
        parsed_pattern = urlparse(pattern_url)

        if not _domains_matches(parsed_pattern.hostname, parsed_url.hostname):
            continue

        if parsed_pattern.path and not _path_matches(
            parsed_pattern.path, parsed_url.path
        ):
            continue

        if parsed_pattern.query and not _qs_matches(
            parsed_pattern.query, parsed_url.query
        ):
            continue

        for tag in parts[1:]:
            result.add(tag)

    return result


def _path_matches(expected_path: str, actual_path: str) -> bool:
    return actual_path.startswith(expected_path)


def _domains_matches(expected_domain: str, actual_domain: str) -> bool:
    expected_domain = idna.encode(expected_domain)
    actual_domain = idna.encode(actual_domain)

    return actual_domain.endswith(expected_domain)


def _qs_matches(expected_qs: str, actual_qs: str) -> bool:
    expected_qs = parse_qs(expected_qs, keep_blank_values=True)
    actual_qs = parse_qs(actual_qs, keep_blank_values=True)

    for key in expected_qs:
        if key not in actual_qs:
            return False
        for value in expected_qs[key]:
            if value != "" and value not in actual_qs[key]:
                return False

    return True
