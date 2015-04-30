import logging
import inspect
from socialfeedharvester.fetchables.resource import UnknownResource
from socialfeedharvester.fetchables.resource_type import WebPagePartType

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

    Resource types are class names of classes from socialfeedharvester.fetchables.resource_type.  They are supertypes
    of relevant fetchable classes.  For example, DocumentType is a superclass of the Pdf fetchable.
    """

    def __init__(self, depth2_resource_types=None, depth3_resource_types=None, webpageparttype_above_depth2=True):
        """
        :param depth2_resource_types:  Class names of resource types to fetch if at depth 2.
        :param depth3_resource_types:  Class names of resource types to fetch if found at depth 3.
        :param webpageparttype_above_depth2:  Fetch WebPagePartTypes at any depth greater than depth 2.
        """
        self.depth2_resource_types = depth2_resource_types or []
        self.depth3_resource_types = depth3_resource_types or []
        self.webpageparttype_above_depth2 = webpageparttype_above_depth2

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
        #Maybe fetch WebPagePartTypes
        elif (self.webpageparttype_above_depth2
              and depth > 2
              and self._in_resource_types(fetchable, (WebPagePartType.__name__,))):
            log.debug("Fetching %s since a web page part type.", fetchable)
            return True
        elif depth == 2:
            if self._in_resource_types(fetchable, self.depth2_resource_types):
                log.debug("Fetching %s since depth is 2 and in resource type list.", fetchable)
                return True
            elif isinstance(fetchable, UnknownResource):
                log.debug("Fetching %s since depth is 2 and an unknown resource.", fetchable)
                return True
        elif depth == 3:
            if self._in_resource_types(fetchable, self.depth3_resource_types):
                log.debug("Fetching %s since depth is 3 and in resource type list.", fetchable)
                return True
            elif isinstance(fetchable, UnknownResource):
                log.debug("Fetching %s since depth is 3 and an unknown resource.", fetchable)
                return True
        log.debug("Not fetching %s.", fetchable)
        return False

    @staticmethod
    def _in_resource_types(fetchable, resource_types):
        for clazz in inspect.getmro(fetchable.__class__):
            if clazz.__name__ in resource_types:
                return True
        return False
