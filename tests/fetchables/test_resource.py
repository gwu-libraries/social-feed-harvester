from tests import TestCase
from mock import MagicMock
from socialfeedharvester.fetchables.resource import *
from sfh import SocialFeedHarvester


class TestHttp(TestCase):
    def setUp(self):
        self.mock_sfh = MagicMock(spec=SocialFeedHarvester)

    def test_process_resource(self):
        html = Html("http://test.com/page.html", None)
        content = """
        <html>
            <head>
                <link rel='stylesheet' id='phoenix-style-css'  href='http://www.wired.com/wp-content/themes/Phoenix/assets/css/style.css?ver=1430166175' type='text/css' media='all' />
                <script type='text/javascript' src='http://www.wired.com/assets/load?scripts=true&amp;c=1&amp;load%5B%5D=jquery-sonar'></script>
            </head>
            <body>
                <img alt="Wired Twitter" class="float-l marg-r-sm marg-b-big" src="http://www.wired.com/wp-content/themes/Phoenix/assets/images/apple-touch-icon.png">
                <img alt="No source" />
                <img src="/images/US-GAO-logo.png" id="gaologotext" itemprop="logo" height="49" width="485" border="0" alt="U.S. Government Accountability Office (GAO)">
            </body>
        </html>
        """
        fetchables = html.process_resource(content, "http://1.test.com/page.html")
        self.assertEqual(4, len(fetchables))
        self.assertIn(CompareResource(Image, "http://www.wired.com/wp-content/themes/Phoenix/assets/images/apple-touch-icon.png"), fetchables)
        self.assertIn(CompareResource(Image, "http://1.test.com/images/US-GAO-logo.png"), fetchables)
        self.assertIn(CompareResource(Stylesheet, "http://www.wired.com/wp-content/themes/Phoenix/assets/css/style.css?ver=1430166175"), fetchables)
        self.assertIn(CompareResource(Script, "http://www.wired.com/assets/load?scripts=true&c=1&load%5B%5D=jquery-sonar"), fetchables)

    def test_redirect(self):
        #1.usa.gov is a shortened url service.  Need to test that linked fetchables are relative to unshortened url.
        self.mock_sfh.is_fetched.return_value = False

        html = Html("http://1.usa.gov/1OVPWl4", self.mock_sfh)
        (warc_records, fetchables) = html.fetch()
        self.assertIn(CompareResource(Image, "http://www.gao.gov/images/US-GAO-logo.png"), fetchables)

    def test_hostname(self):
        html = Html("http://test.com:8080/page.html", None)
        self.assertEqual("test.com", html.hostname)


class TestStylesheet(TestCase):
    def test_process_resource(self):
        stylesheet = Stylesheet("http://test.com/static/test.css", None)

        content = """
        #headerInner {
        background-repeat:repeat-x;
        background-image:url("/inc/gr/bannerbg.jpg");
        border-width:0;
        margin:0;
        padding:0;
        }

        #gaotabs li {
        float:left;
        background:url("/inc/gr/left.gif") no-repeat left top;
        margin:0;
        padding:0 0 0 9px;
        }

        li {
        background:
        url(data:image/gif;base64,R0lGODlhEAAQAMQAAORHHOVSKudfOulrSOp3WOyDZu6QdvCchPGolfO0o/XBs/fNwfjZ0frl3/zy7////wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAkAABAALAAAAAAQABAAAAVVICSOZGlCQAosJ6mu7fiyZeKqNKToQGDsM8hBADgUXoGAiqhSvp5QAnQKGIgUhwFUYLCVDFCrKUE1lBavAViFIDlTImbKC5Gm2hB0SlBCBMQiB0UjIQA7)
        no-repeat
        left center;
        padding: 5px 0 5px 25px;
        }
        """

        fetchables = stylesheet.process_resource(content, "http://1.test.com/static/test.css")
        self.assertEqual(2, len(fetchables))
        self.assertIn(CompareResource(Image, "http://1.test.com/inc/gr/bannerbg.jpg"), fetchables)
        self.assertIn(CompareResource(Image, "http://1.test.com/inc/gr/left.gif"), fetchables)


class CompareResource():
    def __init__(self, clazz, url):
        self.clazz = clazz
        self.url = url

    def __eq__(self, other):
        return isinstance(other, self.clazz) and self.url == other.url