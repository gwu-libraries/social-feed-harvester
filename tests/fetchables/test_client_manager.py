from tests import TestCase
from socialfeedharvester.fetchables.utilities import ClientManager


class TestClient():
    def __init__(self, arg1, arg2, kwarg1, kwarg2):
        self.arg1 = arg1
        self.arg2 = arg2
        self.kwarg1 = kwarg1
        self.kwarg2 = kwarg2
        self.counter = 0


def create_test_client(arg1, arg2, kwarg1=None, kwarg2=None):
    return TestClient(arg1, arg2, kwarg1, kwarg2)


class TestClientManager(TestCase):
    def setUp(self):
        self.client_manager = ClientManager(create_test_client)

    def test_get_client(self):
        c1 = self.client_manager.get_client("a", "b", "c", "d")
        self.assertEqual("a", c1.arg1)
        self.assertEqual("b", c1.arg2)
        self.assertEqual("c", c1.kwarg1)
        self.assertEqual("d", c1.kwarg2)
        self.assertEqual(0, c1.counter)

        #Change counter
        c1.counter = 1

        #Make sure that get same client instead of a new one.
        c2 = self.client_manager.get_client("a", "b", "c", "d")
        c2.counter = 1

    def test_get_client_kwargs(self):
        c1 = self.client_manager.get_client("a", "b", kwarg2="d")
        self.assertEqual("a", c1.arg1)
        self.assertEqual("b", c1.arg2)
        self.assertIsNone(c1.kwarg1)
        self.assertEqual("d", c1.kwarg2)
        self.assertEqual(0, c1.counter)
