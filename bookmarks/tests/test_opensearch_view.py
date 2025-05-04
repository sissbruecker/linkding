from unittest.mock import patch

from django.db import connections
from django.test import TestCase

from xml.etree import ElementTree, XMLSyntaxError

class OpenSearchViewTestCase(TestCase):

    def test_opensearch_parse(self):
        response = self.client.get("/opensearch.xml")

        self.assertEqual(response.status_code, 200)

        with self.assertRaises(XMLSyntaxError):
            ElementTree.fromstring(response.xml())
