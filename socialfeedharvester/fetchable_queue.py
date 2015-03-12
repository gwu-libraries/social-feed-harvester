import collections
import logging

log = logging.getLogger(__name__)

"""
A fetchable queue provides a queue of fetchables.

A fetchable queue should implement the signature of FetchableDeque.  The ordering of the queue is not significant or
guaranteed.
"""


class FetchableDeque():
    """
    A fetchable queue implementation backed by a Dequeue.

    For production use this will need to be backed by a persistent queue.
    """

    def __init__(self):
        self.q = collections.deque()

    def add(self, fetchables, depth=1):
        """
        Adds a single fetchable or a sequence of fetchables to the queue.

        :param fetchables: Fetchables to add.
        :param depth: Level of links from seed, where 1 is a seed.
        """
        if fetchables:
            if isinstance(fetchables, collections.Sequence):
                for fetchable in fetchables:
                    self.add(fetchable, depth)
            else:
                log.debug("Adding to queue: %s (depth=%s)", fetchables, depth)
                self.q.append((fetchables, depth))

    def __len__(self):
        return len(self.q)

    def __iter__(self):
        return self

    def next(self):
        if self.q:
            return self.q.popleft()
        raise StopIteration