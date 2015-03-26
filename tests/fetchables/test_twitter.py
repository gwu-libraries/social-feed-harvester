import tests
import socialfeedharvester.fetchables.twitter as twitter
from mock import MagicMock
from sfh import SocialFeedHarvester
from socialfeedharvester.fetchables.resource import Image, UnknownResource


class TestTwitter(tests.TestCase):
    def setUp(self):
        if not tests.test_config_available:
            self.skipTest("Skipping test since test config not available.")
        self.api = twitter.client_manager.get_client(tests.TWITTER_CONSUMER_KEY, tests.TWITTER_CONSUMER_SECRET,
                                                     access_token = tests.TWITTER_ACCESS_TOKEN,
                                                     access_token_secret = tests.TWITTER_ACCESS_TOKEN_SECRET)
        self.mock_sfh = MagicMock(spec=SocialFeedHarvester)
        self.mock_sfh.get_auth.return_value= {"consumer_key": tests.TWITTER_CONSUMER_KEY,
                                              "consumer_secret": tests.TWITTER_CONSUMER_SECRET,
                                              "access_token": tests.TWITTER_ACCESS_TOKEN,
                                              "access_token_secret": tests.TWITTER_ACCESS_TOKEN_SECRET}

    def test_lookup_user_ids(self):
        user_ids = twitter.lookup_user_ids(("jlittman_dev", "xjlittman_dev"), self.api)
        self.assertEqual(1, len(user_ids))
        self.assertEqual(2875189485, user_ids["jlittman_dev"])

    def test_user_timeline(self):
        u = twitter.UserTimeline(self.mock_sfh, screen_name="jlittman_dev", per_page=3, incremental=False)
        warc_records, fetchables = u.fetch()

        #Warc records
        #3 pages
        self.assertEqual(6, len(warc_records))
        #First should be a request
        self.assertEqual(warc_records[0].type, "request")
        self.assertEqual(warc_records[0].url, "https://api.twitter.com/1.1/statuses/user_timeline.json")
        #And second a response
        self.assertEqual(warc_records[1].type, "response")
        self.assertEqual(warc_records[1].url, "https://api.twitter.com/1.1/statuses/user_timeline.json")

        #Fetchables
        self.assertEqual(2, len(fetchables))
        self.assertIsInstance(fetchables[0], UnknownResource)
        self.assertIsInstance(fetchables[1], Image)

        self.mock_sfh.get_auth.assert_called_with("twitter")

    def test_incremental_user_timeline_no_prev_state(self):
        self.mock_sfh.get_state.return_value = None

        u = twitter.UserTimeline(self.mock_sfh, screen_name="jlittman_dev", per_page=3, incremental=True)
        warc_records, fetchables = u.fetch()

        #Warc records
        #3 pages
        self.assertEqual(6, len(warc_records))

        #Fetchables
        self.assertEqual(2, len(fetchables))

        self.mock_sfh.get_state.assert_called_once_with("socialfeedharvester.fetchables.twitter",
                                                        "jlittman_dev.last_tweet_id")
        self.mock_sfh.set_state.assert_called_once_with("socialfeedharvester.fetchables.twitter",
                                                        "jlittman_dev.last_tweet_id",
                                                        "577866396094242816")

    def test_incremental_user_timeline(self):
        self.mock_sfh.get_state.return_value = "577868039284088832"

        u = twitter.UserTimeline(self.mock_sfh, screen_name="jlittman_dev", per_page=3, incremental=True)
        warc_records, fetchables = u.fetch()

        #Warc records
        #2 pages
        self.assertEqual(4, len(warc_records))

        self.mock_sfh.get_state.assert_called_once_with("socialfeedharvester.fetchables.twitter",
                                                        "jlittman_dev.last_tweet_id")
        self.mock_sfh.set_state.assert_called_once_with("socialfeedharvester.fetchables.twitter",
                                                        "jlittman_dev.last_tweet_id",
                                                        "577866396094242816")
