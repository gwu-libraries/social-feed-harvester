import tests
import socialfeedharvester.fetchables.flickr as flickr
from mock import MagicMock
from sfh import SocialFeedHarvester
from socialfeedharvester.fetchables.resource import Image


class TestFlickr(tests.TestCase):
    def setUp(self):
        if not tests.test_config_available:
            self.skipTest("Skipping test since test config not available.")
        self.api = flickr.client_manager.get_client(tests.FLICKR_KEY, tests.FLICKR_SECRET)
        self.mock_sfh = MagicMock(spec=SocialFeedHarvester)
        self.mock_sfh.get_auth.return_value= {"key": tests.FLICKR_KEY, "secret": tests.FLICKR_SECRET}

    def test_lookup_nsid(self):
        self.assertEqual("131866249@N02", flickr.lookup_nsid("justin.littman", self.api))
        self.assertIsNone(flickr.lookup_nsid("xjustin.littman", self.api))

    def test_user(self):
        #Using a smaller per_page for testing
        u = flickr.User(self.mock_sfh, username="justin.littman", per_page=5, incremental=False)

        #Hostname
        self.assertEqual("api.flickr.com", u.hostname)

        warc_records, fetchables = u.fetch()

        #Warc records
        self.assertEqual(8, len(warc_records))
        #First should be a request
        self.assertEqual(warc_records[0].type, "request")
        #And second a response
        self.assertEqual(warc_records[1].type, "response")

        #Fetchables
        self.assertEqual(12, len(fetchables))
        self.assertIsInstance(fetchables[0], flickr.Photo)

        self.mock_sfh.get_auth.assert_called_with("flickr")

    def test_photo(self):
        p = flickr.Photo("16796603565", "90f7d5c74c", self.mock_sfh, sizes=("Square",))

        #Hostname
        self.assertEqual("api.flickr.com", p.hostname)

        warc_records, fetchables = p.fetch()

        #Warc records for the call to photo info
        self.assertEqual(2, len(warc_records))

        #Fetchable for square
        self.assertEqual(1, len(fetchables))
        self.assertIsInstance(fetchables[0], Image)

    def test_incremental_user_no_prev_state(self):
        self.mock_sfh.get_state.return_value = None

        #Using a smaller per_page for testing
        u = flickr.User(self.mock_sfh, username="justin.littman", per_page=5)
        warc_records, fetchables = u.fetch()

        #Warc records
        self.assertEqual(8, len(warc_records))

        #Fetchables
        self.assertEqual(12, len(fetchables))

        self.mock_sfh.get_state.assert_called_once_with("socialfeedharvester.fetchables.flickr",
                                                        "131866249@N02.last_photo_id")
        self.mock_sfh.set_state.assert_called_once_with("socialfeedharvester.fetchables.flickr",
                                                        "131866249@N02.last_photo_id",
                                                        "16609036938")

    def test_incremental_user_no_new(self):
        self.mock_sfh.get_state.return_value = "16609036938"

        #Using a smaller per_page for testing
        u = flickr.User(self.mock_sfh, username="justin.littman", per_page=5)
        warc_records, fetchables = u.fetch()

        #Warc records
        self.assertEqual(2, len(warc_records))

        #Fetchables
        self.assertEqual(0, len(fetchables))

        self.mock_sfh.get_state.assert_called_once_with("socialfeedharvester.fetchables.flickr",
                                                        "131866249@N02.last_photo_id")
        #Set state should not be called
        self.assertFalse(self.mock_sfh.set_state.called)

    def test_incremental_user(self):
        #16609252680 is the third on the second page
        self.mock_sfh.get_state.return_value = "16609252680"

        #Using a smaller per_page for testing
        u = flickr.User(self.mock_sfh, username="justin.littman", per_page=5)
        warc_records, fetchables = u.fetch()

        #Warc records
        #Last page is omitted
        self.assertEqual(6, len(warc_records))

        #Fetchables
        #2 from last page + 2 from second page
        self.assertEqual(4, len(fetchables))

        self.mock_sfh.get_state.assert_called_once_with("socialfeedharvester.fetchables.flickr",
                                                        "131866249@N02.last_photo_id")
        self.mock_sfh.set_state.assert_called_once_with("socialfeedharvester.fetchables.flickr",
                                                        "131866249@N02.last_photo_id",
                                                        "16609036938")

    def test_incremental_user_first_on_page(self):
        #16176690903 is the first on the second page
        self.mock_sfh.get_state.return_value = "16176690903"

        #Using a smaller per_page for testing
        u = flickr.User(self.mock_sfh, username="justin.littman", per_page=5)
        warc_records, fetchables = u.fetch()

        #Warc records
        #Last page is omitted
        self.assertEqual(6, len(warc_records))

        #Fetchables
        #4 from second page + 2 from last page
        self.assertEqual(6, len(fetchables))

        self.mock_sfh.get_state.assert_called_once_with("socialfeedharvester.fetchables.flickr",
                                                        "131866249@N02.last_photo_id")
        self.mock_sfh.set_state.assert_called_once_with("socialfeedharvester.fetchables.flickr",
                                                        "131866249@N02.last_photo_id",
                                                        "16609036938")

    def test_incremental_user_last_on_page(self):
        #16610484809 is the last on the second page
        self.mock_sfh.get_state.return_value = "16610484809"

        #Using a smaller per_page for testing
        u = flickr.User(self.mock_sfh, username="justin.littman", per_page=5)
        warc_records, fetchables = u.fetch()

        #Warc records
        #Second and last page is omitted
        self.assertEqual(4, len(warc_records))

        #Fetchables
        #2 from last page
        self.assertEqual(2, len(fetchables))

        self.mock_sfh.get_state.assert_called_once_with("socialfeedharvester.fetchables.flickr",
                                                        "131866249@N02.last_photo_id")
        self.mock_sfh.set_state.assert_called_once_with("socialfeedharvester.fetchables.flickr",
                                                        "131866249@N02.last_photo_id",
                                                        "16609036938")

