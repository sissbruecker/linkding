from urllib.parse import urlparse
import re


def get_tags(script: str, url: str):
    parsed_url = urlparse(url.lower())
    result = set()

    for line in script.lower().split("\n"):
        parts = line.split()
        if len(parts) < 2:
            continue

        domain_pattern = re.sub("^https?://", "", parts[0])
        path_pattern = None

        if "/" in domain_pattern:
            i = domain_pattern.index("/")
            path_pattern = domain_pattern[i:]
            domain_pattern = domain_pattern[:i]

        if not parsed_url.netloc.endswith(domain_pattern):
            continue

        if path_pattern and not parsed_url.path.startswith(path_pattern):
            continue

        for tag in parts[1:]:
            result.add(tag)

    return result
