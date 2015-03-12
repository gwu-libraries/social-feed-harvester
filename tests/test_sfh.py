from tests import TestCase
from sfh import SocialFeedHarvester
import tempfile
from mock import MagicMock, call
from socialfeedharvester.fetchable_queue import FetchableDeque
from socialfeedharvester.fetch_strategy import DefaultFetchStrategy
from socialfeedharvester.fetchables.tumblr import Blog
from socialfeedharvester.warc import WarcWriter

class TestSocialFeedHarvester(TestCase):

    def setUp(self):
        self.data_path = tempfile.mkdtemp()

    def test_blog_seed(self):
        mock_fq = MagicMock(spec=FetchableDeque)
        mock_fq.__len__.return_value = 1

        SocialFeedHarvester([
                                {
                                    "type": "blog",
                                    "blog_name": "libraryjournal",
                                    "max_posts": 20
                                },
                            ],
                            fetchable_queue=mock_fq)

        mock_fq.add.assert_called_with(Comparer(lambda other: (isinstance(other, Blog)
                                                               and other.blog_name == "libraryjournal"
                                                               and other.max_posts == 20)), 1)

    def test_fetch(self):

        #Fetchable 1 should not be called because False is returned as the fetch decision.
        mock_f1 = MagicMock(spec=Blog)
        #Fetchable 2 should be called, but does not return any warc records or additional fetchables.
        mock_f2 = MagicMock(spec=Blog)
        mock_f2.fetch.return_value = (None, None)
        #Fetchable 4 returns 2 warc records, which should be passed to warc writer.
        mock_wr1 = MagicMock(name="warc record1")
        mock_wr2 = MagicMock(name="warc record2")
        mock_f4 = MagicMock(spec=Blog)
        mock_f4.fetch.return_value = ((mock_wr1, mock_wr2), None)
        #Fetchable 3 should be called and return fetchable 4.
        mock_f3 = MagicMock(spec=Blog)
        mock_f3.fetch.return_value = (None, (mock_f4,))

        #Fetch strategy
        mock_fs = MagicMock(spec=DefaultFetchStrategy)
        mock_fs.fetch_decision.side_effect = (False, True, True, True)

        #Warc
        mock_ww = MagicMock(spec=WarcWriter)

        sfh = SocialFeedHarvester([],
                                  fetch_strategy=mock_fs,
                                  warc_writer=mock_ww)

        sfh._fetchable_queue.add((mock_f1, mock_f2, mock_f3))
        sfh.fetch()

        self.assertFalse(mock_f1.fetch.called)
        self.assertTrue(mock_f2.fetch.called)
        self.assertTrue(mock_f3.fetch.called)
        self.assertTrue(mock_f4.fetch.called)
        self.assertEqual([call.fetch_decision(mock_f1, 1),
                          call.fetch_decision(mock_f2, 1),
                          call.fetch_decision(mock_f3, 1),
                          call.fetch_decision(mock_f4, 2)], mock_fs.mock_calls)
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