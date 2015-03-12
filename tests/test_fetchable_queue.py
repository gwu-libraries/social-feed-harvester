from socialfeedharvester.fetchable_queue import FetchableDeque
from socialfeedharvester.fetchables.resource import UnsupportedResource
from tests import TestCase


class TestDequeQueue(TestCase):

    def setUp(self):
        self.q = FetchableDeque()

    def test_add_fetchable(self):
        self.q.add(UnsupportedResource("http://example.com/1", None))
        self.assertEqual(1, len(self.q), "Adding a single fetchable not reflected in queue length.")

    def test_add_fetchables(self):
        self.q.add((UnsupportedResource("http://example.com/1", None),
                    UnsupportedResource("http://example.com/2", None)))
        self.assertEqual(2, len(self.q), "Adding a sequence of fetchables not reflected in queue length.")

    def test_iteration(self):
        self.q.add((UnsupportedResource("http://example.com/1", None),
                    UnsupportedResource("http://example.com/2", None)))
        count = 0
        for (fetchable, depth) in self.q:
            count += 1
            self.assertIsInstance(fetchable, UnsupportedResource)
            #Test depth
            if fetchable.url == "http://example.com/3":
                self.assertEqual(2, depth)
            else:
                self.assertEqual(1, depth)
            #Add a fetchable mid-iteration
            if count == 1:
                #Note this is a seed
                self.q.add(UnsupportedResource("http://example.com/3", None), depth=2)
        self.assertEqual(3, 3, "Did not iterate over the correct number of fetchables.")
