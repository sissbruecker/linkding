#!/usr/bin/env python3
import requests
from datetime import datetime


def load_releases_page(page):
    url = f'https://api.github.com/repos/sissbruecker/linkding/releases?page={page}'
    return requests.get(url).json()


def load_all_releases():
    load_next_page = True
    page = 1
    releases = []

    while load_next_page:
        page_result = load_releases_page(page)
        releases = releases + page_result
        load_next_page = len(page_result) > 0
        page = page + 1

    return releases


def render_release_section(release):
    date = datetime.fromisoformat(release['published_at'].replace("Z", "+00:00"))
    formatted_date = date.strftime('%d/%m/%Y')
    section = f'## {release["name"]} ({formatted_date})\n\n'
    body = release['body']
    # increase heading for body content
    body = body.replace("## What's Changed", "### What's Changed")
    body = body.replace("## New Contributors", "### New Contributors")
    section += body.strip()
    return section


def generate_change_log():
    releases = load_all_releases()

    change_log = '# Changelog\n\n'
    sections = [render_release_section(release) for release in releases]
    body = '\n\n---\n\n'.join(sections)
    change_log = change_log + body

    with open("CHANGELOG.md", "w") as file:
        file.write(change_log)


generate_change_log()
