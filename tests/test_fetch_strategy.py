from socialfeedharvester.fetch_strategy import DefaultFetchStrategy
from tests import TestCase
from socialfeedharvester.fetchables.twitter import UserTimeline
from socialfeedharvester.fetchables.resource import Html, UnknownResource, Image


class TestDefaultFetchStrategy(TestCase):

    def setUp(self):
        self.fs = DefaultFetchStrategy(depth2_to_fetch=("Html",))

    def test_not_fetchable(self):
        self.assertFalse(self.fs.fetch_decision(NotFetchableResource(), 1),
                         "Not fetchable resource should not be fetched")

    def test_seed(self):
        self.assertTrue(self.fs.fetch_decision(UserTimeline(screen_name="justin_littman"), 1))

    def test_depth2(self):
        self.assertTrue(self.fs.fetch_decision(Html("http://example.com", None), 2))
        self.assertTrue(self.fs.fetch_decision(UnknownResource("http://example.com", None), 2))
        self.assertFalse(self.fs.fetch_decision(UserTimeline(screen_name="justin_littman"), 2))

    def test_depth3(self):
        #Note that default depth3_to_fetch includes Images.
        self.assertTrue(self.fs.fetch_decision(Image("http://example.com/test.jpg", None), 3))
        self.assertTrue(self.fs.fetch_decision(UnknownResource("http://example.com", None), 3))
        self.assertFalse(self.fs.fetch_decision(UserTimeline(screen_name="justin_littman"), 3))
        self.assertFalse(self.fs.fetch_decision(Image("http://example.com/test.jpg", None), 2))



class NotFetchableResource():
    is_fetchable = False

    def __init__(self):
        pass
