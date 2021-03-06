from socialfeedharvester.fetch_strategy import DefaultFetchStrategy
from tests import TestCase
from socialfeedharvester.fetchables.twitter import UserTimeline
from socialfeedharvester.fetchables.resource import Html, UnknownResource, Image
from socialfeedharvester.fetchables.vimeo import Video


class TestDefaultFetchStrategy(TestCase):

    def setUp(self):
        self.fs = DefaultFetchStrategy(depth2_resource_types=("WebPageType",),
                                       depth3_resource_types=("VideoType",))

    def test_not_fetchable(self):
        self.assertFalse(self.fs.fetch_decision(NotFetchableResource(), 1),
                         "Not fetchable resource should not be fetched")

    def test_seed(self):
        self.assertTrue(self.fs.fetch_decision(UserTimeline(None, screen_name="justin_littman"), 1))

    def test_depth2(self):
        self.assertTrue(self.fs.fetch_decision(Html("http://example.com", None), 2))
        self.assertTrue(self.fs.fetch_decision(UnknownResource("http://example.com", None), 2))
        self.assertFalse(self.fs.fetch_decision(UserTimeline(None, screen_name="justin_littman"), 2))
        self.assertFalse(self.fs.fetch_decision(Image("http://example.com/test.jpg", None), 2))

    def test_depth3(self):
        self.assertTrue(self.fs.fetch_decision(Image("http://example.com/test.jpg", None), 3))
        self.assertTrue(self.fs.fetch_decision(UnknownResource("http://example.com", None), 3))
        self.assertFalse(self.fs.fetch_decision(UserTimeline(None, screen_name="justin_littman"), 3))
        self.assertFalse(self.fs.fetch_decision(Video("http://example.com/test.vid", None), 2))

    def test_depth4(self):
        self.assertTrue(self.fs.fetch_decision(Image("http://example.com/test.jpg", None), 4))
        self.assertFalse(self.fs.fetch_decision(Video("http://example.com/test.vid", None), 4))

class NotFetchableResource():
    is_fetchable = False

    def __init__(self):
        pass
