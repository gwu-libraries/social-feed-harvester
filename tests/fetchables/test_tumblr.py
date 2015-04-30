import tests
import socialfeedharvester.fetchables.tumblr as tumblr
from mock import MagicMock
from sfh import SocialFeedHarvester
from socialfeedharvester.fetchables.resource import Image, UnknownResource
from socialfeedharvester.fetchables.youtube import Video
import pytumblr


class TestTumblr(tests.TestCase):
    def setUp(self):
        if not tests.test_config_available:
            self.skipTest("Skipping test since test config not available.")
        self.mock_sfh = MagicMock(spec=SocialFeedHarvester)
        self.mock_sfh.get_auth.return_value = {"api_key": tests.TUMBLR_API_KEY}
        self.client = pytumblr.TumblrRestClient(tests.TUMBLR_API_KEY)

    def test_blog_incremental_no_change(self):
        #Get most recent post
        posts = self.client.posts("justinlittman-dev", limit=1)
        self.mock_sfh.get_state.return_value = str(posts["posts"][0]["id"])

        b = tumblr.Blog("justinlittman-dev", self.mock_sfh, incremental=True)
        warc_records, fetchables = b.fetch()

        self.assertEqual(0, len(warc_records))
        self.assertEqual(0, len(fetchables))

        self.mock_sfh.get_state.assert_called_once_with("socialfeedharvester.fetchables.tumblr",
                                                        "justinlittman-dev.last_post_id")

    def test_blog_incremental(self):
        #Updated, last_post_id
        self.mock_sfh.get_state.return_value = "113915730303"

        b = tumblr.Blog("justinlittman-dev", self.mock_sfh, incremental=True, per_page=3)
        warc_records, fetchables = b.fetch()

        # 2 pages
        self.assertEqual(2, len(warc_records))
        self.assertEqual(1, len(fetchables))

        self.mock_sfh.get_state.assert_called_once_with("socialfeedharvester.fetchables.tumblr",
                                                        "justinlittman-dev.last_post_id")
        #Most recent post
        posts = self.client.posts("justinlittman-dev", limit=1)
        self.mock_sfh.set_state.assert_called_once_with("socialfeedharvester.fetchables.tumblr",
                                                        "justinlittman-dev.last_post_id",
                                                        str(posts["posts"][0]["id"]))

    def test_blog(self):
        b = tumblr.Blog("justinlittman-dev", self.mock_sfh, incremental=False, per_page=3)

        self.assertEqual("api.tumblr.com", b.hostname)

        warc_records, fetchables = b.fetch()

        # 3 pages
        self.assertEqual(6, len(warc_records))
        self.assertEqual(3, len(fetchables))
        #Link to GWU
        self.assertIsInstance(fetchables[0], UnknownResource)
        #Youtube video
        self.assertIsInstance(fetchables[1], Video)
        #Photo
        self.assertIsInstance(fetchables[2], Image)

        self.assertFalse(self.mock_sfh.get_state.called)
