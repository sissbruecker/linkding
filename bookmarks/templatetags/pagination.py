from functools import reduce

from django import template
from django.core.paginator import Page

NUM_ADJACENT_PAGES = 2

register = template.Library()


@register.inclusion_tag('bookmarks/pagination.html', name='pagination', takes_context=True)
def pagination(context, page: Page):
    visible_page_numbers = get_visible_page_numbers(page.number, page.paginator.num_pages)

    return {
        'page': page,
        'visible_page_numbers': visible_page_numbers
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
    visible_pages |= set(range(
        max(1, current_page_number - NUM_ADJACENT_PAGES),
        min(num_pages, current_page_number + NUM_ADJACENT_PAGES) + 1
    ))

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
