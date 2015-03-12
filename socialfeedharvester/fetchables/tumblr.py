import urllib
import logging

import pytumblr
import oauth2 as oauth
from httplib2 import RedirectLimit
import html5lib
from config import tumblr_api_key
from config import tumblr_post_limit as post_limit
from socialfeedharvester.fetchables.resource import Image, UnknownResource
import youtube
import vimeo
import httplib2 as http_client
from socialfeedharvester.utilities import HttpLibMixin
from socialfeedharvester.utilities import HttLib2ResponseAdapter

log = logging.getLogger(__name__)


class Blog():
    is_fetchable = True

    def __init__(self, blog_name, max_posts, sfh):
        self.blog_name = blog_name
        self.max_posts = max_posts
        self.sfh = sfh

    def __str__(self):
        return "blog %s [max posts=%s]" % (self.blog_name, self.max_posts)

    def fetch(self):
        # Make the request
        (blog, resp, warc_records) = tumblr_client.blog_info(self.blog_name)
        post_count = blog['blog']['posts']
        updated = blog['blog']['updated']

        if self.sfh.get_state(__name__, "%s.updated" % self.blog_name) != updated:
            last_post_id = self.sfh.get_state(__name__, "%s.last_post_id" % self.blog_name)
            starting_offset = 0
            if last_post_id:
                #Try to find offset of last post by walking backwards through posts.
                offsets = list(range(post_count-1, 0, post_limit * -1))
                #Add 0 on the end
                offsets.append(0)
                for offset in offsets:
                    (resp_posts, resp, content) = tumblr_client.posts(self.blog_name, limit=post_limit, offset=offset)
                    for counter, resp_post in enumerate(resp_posts["posts"]):
                        post_offset = offset + counter
                        if resp_post["id"] == last_post_id:
                            starting_offset = post_offset + 1
                            break
            posts = []
            if self.max_posts and (self.max_posts + starting_offset) < post_count:
                post_upper_bound = self.max_posts + starting_offset
            else:
                post_upper_bound = post_count
            log.debug("Queing posts from offset %s to %s." % (starting_offset, post_upper_bound))
            for offset in range(starting_offset, post_upper_bound, post_limit):
                posts.append(Posts(self.blog_name, offset, self.sfh))
            #Set the last one
            posts[-1].is_last = True

            #Set state if fetched all posts
            if post_upper_bound != self.max_posts:
                self.sfh.set_state(__name__, "%s.updated" % self.blog_name, updated)

            return warc_records, reversed(posts)
        else:
            log.debug("No new posts for %s", self.blog_name)
            return None


class Posts():
    is_fetchable = True

    def __init__(self, blog_name, offset, sfh):
        self.blog_name = blog_name
        self.sfh = sfh
        self.offset = offset
        self.is_last = False

    def __str__(self):
        return "blog post %s for %s" % (self.offset, self.blog_name)

    def fetch(self):
        # Make the request
        (posts, resp, warc_records) = tumblr_client.posts(self.blog_name, limit=post_limit,
                offset=self.offset)

        linked_fetchables = []
        for post in posts['posts']:
            post_id = post['id']
            if post['type'] == 'photo':
                for photo in post['photos']:
                    #Seems that first alt size is the biggest
                    url = photo['alt_sizes'][0]['url']
                    linked_fetchables.append(Image(url, self.sfh))
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
                            linked_fetchables.append(youtube.Video(video_url, self.sfh))
                        elif post['video_type'] == 'vimeo':
                            linked_fetchables.append(vimeo.Video(video_url, self.sfh))
            elif post['type'] == 'text':
                #Parse body
                body_fragment = html5lib.parseFragment(post['body'], namespaceHTMLElements=False)
                #Extract links
                for a_elem in body_fragment.findall(".//a[@href]"):
                    linked_fetchables.append(UnknownResource(a_elem.attrib['href'], self.sfh))
                #Extract images
                for img_elem in body_fragment.findall(".//img[@src]"):
                    linked_fetchables.append(Image(img_elem.attrib['src'], self.sfh))
                #TODO:  Consider whether there are other elements that should be parsed.
                #Also, need to test if original is markdown, do we get html or markdown.
            #TODO: Other post types

        #If last, set last_post_id
        if self.is_last:
            last_post_id = posts["posts"][-1]["id"]
            self.sfh.set_state(__name__, "%s.last_post_id" % self.blog_name, last_post_id)

        return warc_records, linked_fetchables


class TumblrRequest(pytumblr.TumblrRequest, HttpLibMixin):
    """
    Replacement for pytumblr.request.TumblrRequest that returns warc records in addition to JSON.
    """
    def get(self, url, params):
        url = self.host + url
        if params:
            url = url + "?" + urllib.urlencode(params)

        client = oauth.Client(self.consumer, self.token)
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

#Create Tumblr client
tumblr_client = pytumblr.TumblrRestClient(tumblr_api_key)
#Replace TumblrRequest
tumblr_client.request = TumblrRequest(tumblr_api_key)
