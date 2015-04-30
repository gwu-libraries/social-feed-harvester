"""
These are marker classes for types of resources.
"""


class AnyResourceType():
    pass


class WebPagePartType(AnyResourceType):
    pass


class ImageType(WebPagePartType):
    pass


class VideoType(AnyResourceType):
    pass


class WebPageType(AnyResourceType):
    pass


class DocumentType(WebPagePartType):
    pass


class FlickrType():
    pass
