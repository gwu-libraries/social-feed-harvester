import logging
import json
import httplib as http_client

from socialfeedharvester.fetchables import resource
import warc
import tweepy
import tweepy.parsers
import os
import socialfeedharvester.fetchables.utilities as utilities
from socialfeedharvester.fetchables.utilities import ClientManager


log = logging.getLogger(__name__)


class TweetWarc():
    is_fetchable = True

    def __init__(self, filepath, sfh):
        self.filepath = filepath
        self.sfh = sfh

    def fetch(self):
        #Open the warc
        log.debug("Opening %s", self.filepath)
        warc_file = warc.WARCFile(filename=self.filepath)
        fetchables = []
        try:
            for warc_record in warc_file:
                #Ignore requests
                if warc_record.type in ("continuation", "response"):
                    log.debug("Processing record %s (%s)", warc_record.header.record_id, warc_record.type)
                    past_http_header = True if warc_record.type == "continuation" else False
                    crlf_count = 0
                    for line in warc_record.payload:
                        #Need to skip past http header if a response
                        if not past_http_header and crlf_count == 2:
                            past_http_header = True
                        if line == "\n":
                            crlf_count += 1
                        else:
                            crlf_count = 0
                        if past_http_header and line != '\n':
                            try:
                                tweet = json.loads(unicode(line))
                            except Exception:
                                log.warn("Malformed tweet in %s: %s", self.filepath, line)
                                continue
                            if 'entities' in tweet and 'urls' in tweet['entities']:
                                for url in tweet['entities']['urls']:
                                    fetchables.append(resource.UnknownResource(url['expanded_url'], self.sfh))
                else:
                    log.debug("Skipping record %s (%s)", warc_record.header.record_id, warc_record.type)
        finally:
            warc_file.close()
            #If warc is a symlink, delete
            if os.path.islink(self.filepath):
                log.debug("Deleting symlink %s", self.filepath)
                os.unlink(self.filepath)

        return None, fetchables

    def __str__(self):
        return "tweet warc at %s" % self.filepath


class UserTimeline(utilities.HttpLibMixin):
    is_fetchable = True

    def __init__(self, sfh, user_id=None, screen_name=None, incremental=True, per_page=None):
        self.sfh = sfh
        assert user_id or screen_name
        assert not (user_id and screen_name)
        self.user_id = user_id
        self.screen_name = screen_name
        #Allowing a null sfh is for testing purposes only.
        if sfh:
            self.api = get_api(self.sfh)
        else:
            log.warning("Using a null sfh. This should be used for testing only.")
        #Per page is for testing only.
        self.per_page = per_page
        self.incremental = incremental

    def fetch(self):
        self.api.parser = tweepy.parsers.RawParser()

        last_tweet_id = self.sfh.get_state(__name__, "%s.last_tweet_id" % (self.user_id or self.screen_name)) \
            if self.incremental else None


        page = 1
        warc_records = []
        fetchables = []
        new_last_tweet_id = None
        while True:
            tweets_resp, capture_out = self.wrap_execute(
                lambda: self.api.user_timeline(page=page, screen_name=self.screen_name, user_id=self.user_id,
                                               count=self.per_page, max_id=last_tweet_id),
                http_client.HTTPConnection)
            http_headers = self.parse_capture(capture_out)
            if tweets_resp != '[]':
                #Write request and response
                assert len(http_headers) == 2
                url = "https://%s%s" % (self.api.host, self.parse_url(http_headers[0]))
                #Write request
                warc_records.append((self.to_warc_record("request", url,
                                                           http_header=http_headers[0])))
                #Write response
                warc_records.append(self.to_warc_record("response", url, http_body=tweets_resp,
                                                  http_header=http_headers[1]))

                #print statuses
                tweets = json.loads(tweets_resp)
                for tweet in tweets:
                    new_last_tweet_id = tweet["id"]
                    if "urls" in tweet["entities"]:
                        for url in tweet["entities"]["urls"]:
                            fetchables.append(resource.UnknownResource(url['expanded_url'], self.sfh))
                    if "media" in tweet["entities"]:
                        for media in tweet["entities"]["media"]:
                            fetchables.append(resource.Image(media["media_url"], self.sfh))

            else:
                # All done
                break
            page += 1  # next page
        if self.incremental and new_last_tweet_id:
            self.sfh.set_state(__name__, "%s.last_tweet_id" % (self.user_id or self.screen_name), str(new_last_tweet_id))

        return warc_records, fetchables

    def __str__(self):
        return "user timeline of %s" % (self.screen_name or self.user_id)


def lookup_user_ids(screen_names, api):
    """
    Returns a mapping of screen names to user ids for a provided list of screen names.

    Note that if a screen name is not found, it will be omitted from the result.
    """
    if isinstance(screen_names, basestring):
        screen_names = (screen_names,)
    api.parser = tweepy.parsers.ModelParser()
    users = api.lookup_users(screen_names=screen_names)
    result = {}
    for user in users:
        result[user.screen_name] = user.id
    not_found = list(set(screen_names) - set(users))
    if not_found:
        log.warn("Screen names not found: %s", not_found)
    return result


def create_twitter_client(consumer_key, consumer_secret, access_token=None, access_token_secret=None):
    #Construct auth
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    if access_token and access_token_secret:
        auth.set_access_token(access_token, access_token_secret)
        # Construct the API instance
    return tweepy.API(auth)

client_manager = ClientManager(create_twitter_client)


def get_api(sfh):
    auth = sfh.get_auth("twitter")
    return client_manager.get_client(auth["consumer_key"], auth["consumer_secret"],
                                     access_token=auth.get("access_token"), access_token_secret=auth.get("access_token_secret"))