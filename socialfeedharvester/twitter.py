import logging
import warc
import json
import resource
import tweepy
import tweepy.parsers
import config
import os
import utilities
import httplib as http_client

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
                                    self.sfh.queue_append(resource.UnknownResource(url['expanded_url'], self.sfh))
                else:
                    log.debug("Skipping record %s (%s)", warc_record.header.record_id, warc_record.type)
        finally:
            warc_file.close()
            #If warc is a symlink, delete
            if os.path.islink(self.filepath):
                log.debug("Deleting symlink %s", self.filepath)
                os.unlink(self.filepath)

        return None

    def __str__(self):
        return "tweet warc at %s" % self.filepath

class UserTimeline(utilities.HttpLibMixin):
    is_fetchable = True

    def __init__(self, user_id=None, screen_name=None):
        assert user_id or screen_name
        self.user_id = user_id
        self.screen_name = screen_name
        self.url = "https://%s/statuses/user_timeline.json" % api.api_root

    def fetch(self):
        api.parser = tweepy.parsers.RawParser()
        #api.wait_on_rate_limit = True
        #api.wait_on_rate_limit_notify = True
        page = 1
        warc_records = []
        while True:
            statuses, capture_out = self.wrap_execute(
                lambda: api.user_timeline(page=page, screen_name=self.screen_name, count=200),
                http_client.HTTPConnection)
            http_headers = self.parse_capture(capture_out)
            if statuses != '[]':
                #Write request and response
                assert len(http_headers) == 2
                #Write request
                warc_records.append((self.to_warc_record("request", self.url,
                                                           http_header=http_headers[0])))
                #Write response
                warc_records.append(self.to_warc_record("response", self.url, http_body=statuses,
                                                  http_header=http_headers[1]))

            else:
                # All done
                break
            page += 1  # next page
        return warc_records

    def __str__(self):
        return "user timeline of %s" % self.screen_name or self.user_id


def lookup_user_ids(screen_names):
    """
    Returns a mapping of screen names to user ids for a provided list of screen names.

    Note that if a screen name is not found, it will be omitted from the result.
    """
    users = api.lookup_users(screen_names=screen_names)
    result = {}
    for user in users:
        result[user.screen_name] = user.id
    not_found = list(set(screen_names) - set(users))
    if not_found:
        log.warn("Screen names not found: %s", not_found)
    return result

#Construct auth
auth = tweepy.OAuthHandler(config.twitter_consumer_key, config.twitter_consumer_secret)
auth.set_access_token(config.twitter_access_token, config.twitter_access_token_secret)
# Construct the API instance
api = tweepy.API(auth)