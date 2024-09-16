from functools import reduce

from django import template
from django.core.paginator import Page
from django.http import QueryDict

NUM_ADJACENT_PAGES = 2

register = template.Library()


@register.inclusion_tag(
    "bookmarks/pagination.html", name="pagination", takes_context=True
)
def pagination(context, page: Page):
    # remove page number and details from query parameters
    query_params = context["request"].GET.copy()
    query_params.pop("page", None)
    query_params.pop("details", None)

    prev_link = (
        _generate_link(query_params, page.previous_page_number())
        if page.has_previous()
        else None
    )
    next_link = (
        _generate_link(query_params, page.next_page_number())
        if page.has_next()
        else None
    )

    visible_page_numbers = get_visible_page_numbers(
        page.number, page.paginator.num_pages
    )
    page_links = []
    for page_number in visible_page_numbers:
        if page_number == -1:
            page_links.append(None)
        else:
            link = _generate_link(query_params, page_number)
            page_links.append(
                {
                    "active": page_number == page.number,
                    "number": page_number,
                    "link": link,
                }
            )

    return {
        "prev_link": prev_link,
        "next_link": next_link,
        "page_links": page_links,
    }


def get_visible_page_numbers(current_page_number: int, num_pages: int) -> [int]:
    """
    Generates a list of page indexes that should be rendered
    The list can contain "holes" which indicate that a range of pages are truncated
    Holes are indicated with a value of `-1`
    :param current_page_number:
    :param num_pages:
    """
    visible_pages = set()

    # Add adjacent pages around current page
    visible_pages |= set(
        range(
            max(1, current_page_number - NUM_ADJACENT_PAGES),
            min(num_pages, current_page_number + NUM_ADJACENT_PAGES) + 1,
        )
    )

    # Add first page
    visible_pages.add(1)

    # Add last page
    visible_pages.add(num_pages)

    # Convert to sorted list
    visible_pages = list(visible_pages)
    visible_pages.sort()

    def append_page(result: [int], page_number: int):
        # Look for holes and insert a -1 as indicator
        is_hole = len(result) > 0 and result[-1] < page_number - 1
        if is_hole:
            result.append(-1)
        result.append(page_number)
        return result

    return reduce(append_page, visible_pages, [])


def _generate_link(query_params: QueryDict, page_number: int) -> str:
    query_params["page"] = page_number
    return query_params.urlencode()
