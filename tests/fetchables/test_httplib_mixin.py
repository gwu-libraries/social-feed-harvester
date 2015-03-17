from tests import TestCase
from socialfeedharvester.fetchables.utilities import HttpLibMixin


class TestClientManager(TestCase):
    def setUp(self):
        self.mixin = HttpLibMixin()

    def test_parse_url(self):
        self.assertEqual("/services/rest/?nojsoncallback=1&user_id=131866249%40N02&method=flickr.people.getInfo&format=json",
                         self.mixin.parse_url("""GET /services/rest/?nojsoncallback=1&user_id=131866249%40N02&method=flickr.people.getInfo&format=json HTTP/1.1
                            Host: api.flickr.com
                            Connection: close
                            Authorization: OAuth oauth_nonce="130392106724740835301426189240", oauth_timestamp="1426189240", oauth_version="1.0", oauth_signature_method="HMAC-SHA1", oauth_consumer_key="abddfe6fb8bba36e8ef0278ec65dbbc8", oauth_signature="%2B67oTwPzV3NxB1pwUTLR44VP860%3D"
                            Accept-Encoding: gzip, deflate
                            Accept: */*
                            User-Agent: python-requests/2.3.0 CPython/2.7.8 Darwin/13.4.0"""))
