from tests import TestCase, TUMBLR_API_KEY
from sfh import SocialFeedHarvester
import tempfile
from mock import MagicMock, call
from socialfeedharvester.fetchable_queue import FetchableDeque
from socialfeedharvester.fetch_strategy import DefaultFetchStrategy
from socialfeedharvester.fetchables.tumblr import Blog
from socialfeedharvester.fetchables.resource import UnknownResource
from socialfeedharvester.warc import WarcWriter


class TestSocialFeedHarvester(TestCase):

    def setUp(self):
        self.data_path = tempfile.mkdtemp()

    def test_blog_seed(self):
        mock_fq = MagicMock(spec=FetchableDeque)
        mock_fq.__len__.return_value = 1

        SocialFeedHarvester([
                                {
                                    "type": "tumblr_blog",
                                    "blog_name": "libraryjournal",
                                },
                            ],
                            fetchable_queue=mock_fq,
                            auths={"tumblr": {"api_key": TUMBLR_API_KEY}})
        mock_fq.add.assert_called_with(Comparer(lambda other: (isinstance(other, Blog)
                                                               and other.blog_name == "libraryjournal")), 1)

    def test_fetch(self):

        #Fetchable 1 should not be called because False is returned as the fetch decision.
        mock_f1 = MagicMock(spec=Blog, name="f1")
        #Fetchable 2 should be called, but does not return any warc records or additional fetchables.
        mock_f2 = MagicMock(spec=Blog, name="f2")
        mock_f2.fetch.return_value = (None, None)
        #Fetchable 4 returns 2 warc records, which should be passed to warc writer.
        mock_wr1 = MagicMock(name="warc record1")
        mock_wr2 = MagicMock(name="warc record2")
        mock_f4 = MagicMock(spec=Blog, name="f4")
        mock_f4.fetch.return_value = ((mock_wr1, mock_wr2), None)
        #Fetchable 3 should be called and return fetchable 4.
        mock_f3 = MagicMock(spec=Blog, name="f3")
        mock_f3.fetch.return_value = (None, (mock_f4,))

        #Fetchable 5 is an UnknownResource which will return fetchable 6.
        #Fetchable 6 should be at depth 1 (instead of 2).
        mock_f6 = MagicMock(spec=Blog, name="f6")
        mock_f6.fetch.return_value = (None, None)
        mock_f5 = MagicMock(spec=UnknownResource, name="f5")
        mock_f5.fetch.return_value = (None, (mock_f6,))

        #Fetch strategy
        mock_fs = MagicMock(spec=DefaultFetchStrategy)
        mock_fs.fetch_decision.side_effect = (False, True, True, True, True, True)

        #Warc
        mock_ww = MagicMock(spec=WarcWriter)



        sfh = SocialFeedHarvester([],
                                  fetch_strategy=mock_fs,
                                  warc_writer=mock_ww)

        sfh._fetchable_queue.add((mock_f1, mock_f2, mock_f3, mock_f5))
        sfh.fetch()

        self.assertFalse(mock_f1.fetch.called)
        self.assertTrue(mock_f2.fetch.called)
        self.assertTrue(mock_f3.fetch.called)
        self.assertTrue(mock_f4.fetch.called)
        self.assertTrue(mock_f5.fetch.called)
        self.assertTrue(mock_f6.fetch.called)
        self.assertEqual([call.fetch_decision(mock_f1, 1),
                          call.fetch_decision(mock_f2, 1),
                          call.fetch_decision(mock_f3, 1),
                          call.fetch_decision(mock_f5, 1),
                          call.fetch_decision(mock_f4, 2),
                          call.fetch_decision(mock_f6, 1)], mock_fs.mock_calls)
        self.assertEqual([call.write_record(mock_wr1),
                          call.write_record(mock_wr2),
                          call.close()], mock_ww.mock_calls)

    def test_get_auth(self):
        sfh = SocialFeedHarvester([],
                                  auths={"twitter": {"token": "1234"}, "flickr": {"secret": "4567"}})

        self.assertEqual("1234", sfh.get_auth("twitter")["token"])
        self.assertEqual("4567", sfh.get_auth("flickr")["secret"])
        self.assertFalse(sfh.get_auth("tumblr"))


class Comparer():
    def __init__(self, compare):
        self.compare = compare

    def __eq__(self, other):
        return self.compare(other)