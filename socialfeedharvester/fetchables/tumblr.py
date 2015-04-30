import urllib
import logging

import pytumblr
import oauth2 as oauth
from httplib2 import RedirectLimit
import html5lib
from socialfeedharvester.fetchables.resource import Image, UnknownResource
import youtube
import vimeo
import httplib2 as http_client
from socialfeedharvester.fetchables.utilities import HttpLibMixin, ClientManager
from socialfeedharvester.utilities import HttLib2ResponseAdapter

log = logging.getLogger(__name__)


class Blog():
    is_fetchable = True

    def __init__(self, blog_name, sfh, incremental=True, per_page=20):
        self.blog_name = blog_name
        self.incremental = incremental
        #per_page is for testing only
        self.per_page = per_page
        self.sfh = sfh
        #Allowing a null sfh is for testing purposes only.
        if sfh:
            self.client = get_client(self.sfh)
        else:
            log.warning("Using a null sfh. This should be used for testing only.")

    def __str__(self):
        return "blog %s" % (self.blog_name,)

    def fetch(self):
        #Request blog info to get post_count
        (blog, blog_resp, blog_warc_records) = self.client.blog_info(self.blog_name)
        post_count = blog['blog']['posts']
        last_post_id = self.sfh.get_state(__name__, "%s.last_post_id" % self.blog_name) if self.incremental else False

        warc_records = []
        fetchables = []

        new_last_post_id = None
        for offset in range(0, post_count, self.per_page):
            #Make calls to posts
            log.debug("Getting %s posts starting with %s", self.per_page, offset)
            (posts, post_resp, post_warc_records) = self.client.posts(self.blog_name,
                                                                      limit=self.per_page, offset=offset)

            add_warc_records = True
            found_last_post_id = False
            for counter, post in enumerate(posts["posts"]):
                post_id = str(post["id"])
                if post_id == last_post_id:
                    log.debug("Post at position %s is last_post_id (%s)", counter, last_post_id)
                    found_last_post_id = True
                    if counter == 0:
                        add_warc_records = False
                    break
                fetchables.extend(self._process_post(post))
                if new_last_post_id is None:
                    new_last_post_id = post_id

            if add_warc_records:
                warc_records.extend(post_warc_records)

            if found_last_post_id:
                break

        if self.incremental and new_last_post_id:
            self.sfh.set_state(__name__, "%s.last_post_id" % self.blog_name, new_last_post_id)

        return warc_records, fetchables

    def _process_post(self, post):
        fetchables = []
        if post['type'] == 'photo':
            for photo in post['photos']:
                #Seems that first alt size is the biggest
                url = photo['alt_sizes'][0]['url']
                fetchables.append(Image(url, self.sfh))
        elif post['type'] == 'video':
            #Video type:  youtube, vimeo, unknown
            #source_url is only present sometimes
            #To do:  download the video.
            #Perhaps use https://github.com/NFicano/pytube to download Youtube
            #Youtube and Vimeo are embedded with iframe, where src is link to video
            video_url = "None"
            if post['video_type'] in ('youtube', 'vimeo'):
                #May have videos that do no have players.  (I think they are reblogs of videos.)
                #Parse the embed_code
                embed_code = post['player'][0]['embed_code']
                if embed_code:
                    player_fragment = html5lib.parseFragment(embed_code)
                    video_url = player_fragment[0].attrib['src']
                    #Vimeo omits http
                    if video_url.startswith("//"):
                        video_url = "http:" + video_url
                    if post['video_type'] == 'youtube':
                        fetchables.append(youtube.Video(video_url, self.sfh))
                    elif post['video_type'] == 'vimeo':
                        fetchables.append(vimeo.Video(video_url, self.sfh))
        elif post['type'] == 'text':
            #Parse body
            body_fragment = html5lib.parseFragment(post['body'], namespaceHTMLElements=False)
            #Extract links
            for a_elem in body_fragment.findall(".//a[@href]"):
                fetchables.append(UnknownResource(a_elem.attrib['href'], self.sfh))
            #Extract images
            for img_elem in body_fragment.findall(".//img[@src]"):
                fetchables.append(Image(img_elem.attrib['src'], self.sfh))
            #TODO:  Consider whether there are other elements that should be parsed.
            #Also, need to test if original is markdown, do we get html or markdown.
        #TODO: Other post types

        return fetchables


class TumblrRequest(pytumblr.TumblrRequest, HttpLibMixin):
    """
    Replacement for pytumblr.request.TumblrRequest that returns warc records in addition to JSON.
    """
    def get(self, url, params):
        url = self.host + url
        if params:
            url = url + "?" + urllib.urlencode(params)

        client = oauth.Client(self.consumer, self.token)
        warc_records = []
        try:
            client.follow_redirects = False
            #http_client.debuglevel = 1
            ((resp, content), capture_out) = self.wrap_execute(
                lambda: client.request(url, method="GET", redirections=False),
                http_client)
            warc_records = self.to_warc_records(capture_out, [HttLib2ResponseAdapter(resp, content)])
        except RedirectLimit, e:
            resp, content = e.args

        return self.json_parse(content), resp, warc_records


def create_tumblr_client(api_key):
    #Create Tumblr client
    tumblr_client = pytumblr.TumblrRestClient(api_key)
    #Replace TumblrRequest
    tumblr_client.request = TumblrRequest(api_key)

    return tumblr_client

client_manager = ClientManager(create_tumblr_client)


def get_client(sfh):
    auth = sfh.get_auth("tumblr")
    return client_manager.get_client(auth["api_key"])