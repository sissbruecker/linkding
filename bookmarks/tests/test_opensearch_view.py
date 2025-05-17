from django.test import TestCase
from django.urls import reverse


class OpenSearchViewTestCase(TestCase):

    def test_opensearch_configuration(self):
        response = self.client.get(reverse("linkding:opensearch"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["content-type"], "application/opensearchdescription+xml"
        )

        base_url = "http://testserver"
        expected_content = f"""
            <OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/" xmlns:moz="http://www.mozilla.org/2006/browser/search/">
                <ShortName>Linkding</ShortName>
                <Description>Linkding</Description>
                <InputEncoding>UTF-8</InputEncoding>
                <Image width="16" height="16" type="image/x-icon">{base_url}/static/favicon.ico</Image>
                <Url type="text/html" template="{base_url}/bookmarks?client=opensearch&amp;q={{searchTerms}}"/>
            </OpenSearchDescription>
        """
        content = response.content.decode()
        self.assertXMLEqual(content, expected_content)
