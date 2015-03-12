import logging
from socialfeedharvester.fetchables.resource import UnknownResource

log = logging.getLogger(__name__)

"""
A fetch strategy determines if a fetchable should be fetched.

A fetch strategy should implement the signature of DefaultFetchStrategy.
"""


class DefaultFetchStrategy():
    """
    A default fetch strategy for fetching with a limited depth.

    The strategy is intended to support:
    * Depth=1 (seeds):  Always fetch.
    * Depth=2 (references in seeds):  Optionally fetch.
    * Depth=3 (references in depth 2 resources):  Fetch, when necessary for rendering (e.g., CSS or Images).

    This strategy is intended to support harvesting at a limited depth, rather than more general recursive harvesting.
    """

    def __init__(self, depth2_to_fetch=None, depth3_to_fetch=("Image",)):
        """
        :param depth2_to_fetch:  Class names of fetchables to fetch if at depth 2.
        :param depth3_to_fetch:  Class names of fetchables to fetch if found at depth 3.
        """
        self.depth2_to_fetch = depth2_to_fetch or []
        self.depth3_to_fetch = depth3_to_fetch or []

    def fetch_decision(self, fetchable, depth):
        """
        Returns True if fetchable should be fetched.
        """
        #Don't fetch if not fetchable
        if not fetchable.is_fetchable:
            log.debug("Not fetching %s since it is not fetchable.", fetchable)
            return False
        #Always fetch depth 1:
        elif depth == 1:
            log.debug("Fetching %s since it is a seed.", fetchable)
            return True
        elif depth == 2:
            if self._in_to_fetch(fetchable, self.depth2_to_fetch):
                log.debug("Fetching %s since depth is 2 and in to fetch list.", fetchable)
                return True
            elif isinstance(fetchable, UnknownResource):
                log.debug("Fetching %s since depth is 2 and an unknown resource.", fetchable)
                return True
        elif depth == 3:
            if self._in_to_fetch(fetchable, self.depth3_to_fetch):
                log.debug("Fetching %s since depth is 3 and in to fetch list.", fetchable)
                return True
            elif isinstance(fetchable, UnknownResource):
                log.debug("Fetching %s since depth is 3 and an unknown resource.", fetchable)
                return True
        log.debug("Not fetching %s.", fetchable)
        return False

    def _in_to_fetch(self, fetchable, to_fetch):
        #TODO:  This should take into account class hierarchies.
        return fetchable.__class__.__name__ in to_fetch