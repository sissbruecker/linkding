from typing import List

from bs4 import BeautifulSoup
from django.template import Template, RequestContext
from django.test import TestCase, RequestFactory

from bookmarks.models import Tag, User
from bookmarks.tests.helpers import BookmarkFactoryMixin


class TagCloudTagTest(TestCase, BookmarkFactoryMixin):
    def make_soup(self, html: str):
        return BeautifulSoup(html, features="html.parser")

    def render_template(self, tags: List[Tag], selected_tags: List[Tag] = [], url: str = '/test'):
        rf = RequestFactory()
        request = rf.get(url)
        context = RequestContext(request, {
            'request': request,
            'tags': tags,
            'selected_tags': selected_tags,
        })
        template_to_render = Template(
            '{% load bookmarks %}'
            '{% tag_cloud tags selected_tags %}'
        )
        return template_to_render.render(context)

    def assertTagGroups(self, rendered_template: str, groups: List[List[str]]):
        soup = self.make_soup(rendered_template)
        group_elements = soup.select('p.group')

        self.assertEqual(len(group_elements), len(groups))

        for group_index, tags in enumerate(groups, start=0):
            group_element = group_elements[group_index]
            link_elements = group_element.select('a')

            self.assertEqual(len(link_elements), len(tags))

            for tag_index, tag in enumerate(tags, start=0):
                link_element = link_elements[tag_index]
                self.assertEqual(link_element.text.strip(), tag)

    def assertNumSelectedTags(self, rendered_template: str, count: int):
        soup = self.make_soup(rendered_template)
        link_elements = soup.select('p.selected-tags a')
        self.assertEqual(len(link_elements), count)

    def test_group_alphabetically(self):
        tags = [
            self.setup_tag(name='Cockatoo'),
            self.setup_tag(name='Badger'),
            self.setup_tag(name='Buffalo'),
            self.setup_tag(name='Chihuahua'),
            self.setup_tag(name='Alpaca'),
            self.setup_tag(name='Coyote'),
            self.setup_tag(name='Aardvark'),
            self.setup_tag(name='Bumblebee'),
            self.setup_tag(name='Armadillo'),
        ]

        rendered_template = self.render_template(tags)

        self.assertTagGroups(rendered_template, [
            [
                'Aardvark',
                'Alpaca',
                'Armadillo',
            ],
            [
                'Badger',
                'Buffalo',
                'Bumblebee',
            ],
            [
                'Chihuahua',
                'Cockatoo',
                'Coyote',
            ],
        ])

    def test_no_duplicate_tag_names(self):
        user1 = User.objects.create_user('user1', 'user1@example.com', 'password123')
        user2 = User.objects.create_user('user2', 'user2@example.com', 'password123')
        user3 = User.objects.create_user('user3', 'user3@example.com', 'password123')

        tags = [
            self.setup_tag(name='shared', user=user1),
            self.setup_tag(name='shared', user=user2),
            self.setup_tag(name='shared', user=user3),
        ]

        rendered_template = self.render_template(tags)

        self.assertTagGroups(rendered_template, [
            [
                'shared',
            ],
        ])

    def test_selected_tags(self):
        tags = [
            self.setup_tag(name='tag1'),
            self.setup_tag(name='tag2'),
            self.setup_tag(name='tag3'),
            self.setup_tag(name='tag4'),
            self.setup_tag(name='tag5'),
        ]
        selected_tags = [
            tags[0],
            tags[1],
        ]

        rendered_template = self.render_template(tags, selected_tags, url='/test?q=%23tag1 %23tag2 %23tag3')

        self.assertNumSelectedTags(rendered_template, 2)

        self.assertInHTML('''
            <a href="?q=%23tag2+%23tag3"
               class="text-bold mr-2">
                <span>-tag1</span>
            </a>
        ''', rendered_template)

        self.assertInHTML('''
            <a href="?q=%23tag1+%23tag3"
               class="text-bold mr-2">
                <span>-tag2</span>
            </a>
        ''', rendered_template)

    def test_selected_tags_are_excluded_from_groups(self):
        tags = [
            self.setup_tag(name='tag1'),
            self.setup_tag(name='tag2'),
            self.setup_tag(name='tag3'),
            self.setup_tag(name='tag4'),
            self.setup_tag(name='tag5'),
        ]
        selected_tags = [
            tags[0],
            tags[1],
        ]

        rendered_template = self.render_template(tags, selected_tags)

        self.assertTagGroups(rendered_template, [
            ['tag3', 'tag4', 'tag5']
        ])
