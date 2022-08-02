from typing import List

from bs4 import BeautifulSoup
from django.template import Template, RequestContext
from django.test import TestCase, RequestFactory

from bookmarks.models import Tag, User
from bookmarks.tests.helpers import BookmarkFactoryMixin


class TagCloudTagTest(TestCase, BookmarkFactoryMixin):
    def make_soup(self, html: str):
        return BeautifulSoup(html, features="html.parser")

    def render_template(self, tags: List[Tag], url: str = '/test'):
        rf = RequestFactory()
        request = rf.get(url)
        context = RequestContext(request, {
            'request': request,
            'tags': tags,
        })
        template_to_render = Template(
            '{% load bookmarks %}'
            '{% tag_cloud tags %}'
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
