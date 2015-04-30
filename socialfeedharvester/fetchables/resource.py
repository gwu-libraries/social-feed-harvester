from socialfeedharvester.fetchables.utilities import HttpLibMixin
import requests
import logging
import re
from bs4 import BeautifulSoup
import urlparse
import httplib as http_client
from socialfeedharvester.fetchables.resource_type import ImageType, DocumentType, WebPageType, AnyResourceType, \
    WebPagePartType

log = logging.getLogger(__name__)


def _str(class_, url):
    return "%s %s" % (re.sub(r"(\w)([A-Z])", r"\1 \2", class_.__name__), url)


class Resource(HttpLibMixin, AnyResourceType):
    is_fetchable = True

    def __init__(self, url, sfh):
        self.url = url
        self.sfh = sfh

    def __str__(self):
        return _str(self.__class__, self.url)

    def __repr__(self):
        return self.__str__()

    def fetch(self):
            warc_records = []
            linked_fetchables = []
            if not self.sfh.is_fetched(self.url):
                #List of responses. Due to redirects, there may be multiple responses.
                resps = []

                resp, capture_out = self.wrap_execute(
                    lambda: requests.get(self.url, hooks={"response": lambda r, *args, **kwargs: resps.append(r)}),
                    http_client.HTTPConnection)

                if resp:
                    linked_fetchables = self.process_resource(resp.content, resps[-1].url)
                    for resp in resps:
                        self.sfh.set_fetched(resp.url)
                    warc_records = self.to_warc_records(capture_out, resps)
                else:
                    log.warn("Getting %s returned %s", self.url, resp.status_code)
                    self.sfh.set_fetched(self.url)
            else:
                log.debug("%s already fetched.", self.url)

            return warc_records, linked_fetchables

    def process_resource(self, content, url):
        """
        Override this to perform additional processing of the content, e.g., to queue additional fetches.

        :returns List of linked fetchables.
        """
        return []


class Image(Resource, ImageType):
    def __init__(self, url, sfh):
        Resource.__init__(self, url, sfh)


class Pdf(Resource, DocumentType):
    def __init__(self, url, sfh):
        Resource.__init__(self, url, sfh)


class Stylesheet(Resource, WebPagePartType):
    def __init__(self, url, sfh):
        Resource.__init__(self, url, sfh)


class Script(Resource, WebPagePartType):
    def __init__(self, url, sfh):
        Resource.__init__(self, url, sfh)


class Html(Resource, WebPageType):
    def __init__(self, url, sfh):
        Resource.__init__(self, url, sfh)

    def process_resource(self, content, url):
        try:
            doc = BeautifulSoup(content)
        except Exception:
            log.warn("Error parsing %s", self.url)
            return
        linked_fetchables = []
        #Images
        for img in doc.find_all("img", src=True):
            linked_fetchables.append(Image(urlparse.urljoin(url, img["src"]), self.sfh))
        #Stylesheets
        # <link rel='stylesheet' id='phoenix-style-css'  href=
        for ss in doc.find_all("link", rel="stylesheet", href=True):
            linked_fetchables.append(Stylesheet(urlparse.urljoin(url, ss["href"]), self.sfh))
        #Script
        # <script type='text/javascript' src=
        for scr in doc.find_all("script", src=True):
            linked_fetchables.append(Script(urlparse.urljoin(url, scr["src"]), self.sfh))

        return linked_fetchables


class UnsupportedResource():
    is_fetchable = False

    def __init__(self, url, sfh):
        self.url = url

    def __str__(self):
        return _str(self.__class__, self.url)

    def __repr__(self):
        return self.__str__()

    def fetch(self):
        raise NotImplementedError


class UnknownResource():
    """
    A resource whose type is not known.

    When fetched, a HEAD is performed for the resource.  If the type can be determined from the content-type header
    and fetching of that type is supported, a new item of that type is queued.
    """
    is_fetchable = True

    def __init__(self, url, sfh):
        self.url = url
        self.sfh = sfh

    def __str__(self):
        return _str(self.__class__, self.url)

    def __repr__(self):
            return self.__str__()

    def fetch(self):
        fetchable = None
        if not self.sfh.is_fetched(self.url):
            resp = requests.head(self.url, allow_redirects=True)
            if resp:
                if 'content-type' in resp.headers:
                    if resp.headers['content-type'].startswith("text/html"):
                        fetchable = Html(self.url, self.sfh)
                    elif resp.headers['content-type'].startswith("image/"):
                        fetchable = Image(self.url, self.sfh)
                    elif resp.headers['content-type'].startswith("application/pdf"):
                        fetchable = Pdf(self.url, self.sfh)
                    else:
                        log.debug("Content-type of %s is %s", self.url, resp.headers['content-type'])
                else:
                    log.warn("%s does not have a content-type header", self.url)
            else:
                log.warn("Result of head of %s was %s", self.url, resp.status_code)
        else:
            log.debug("%s already fetched.", self.url)

        return None, fetchable