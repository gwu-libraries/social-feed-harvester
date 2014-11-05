from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream
import config
import time
import os
import logging
import warc
from socialfeedharvester.utilities import HttpLibMixin
import requests
import httplib as http_client
import socialfeedharvester.utilities as utilities
import socialfeedharvester.twitter as twitter

"""
Harvests from Twitter streaming api to warc files.

With the Twitter streaming api, an http connection is kept open for a long period.  Because of this:
* the payload must be spread across multiple warc records in multipkle warc files
* related content is not fetched at the same time as the tweets.

The payload is spread across multiple warc records using the warc continuation mechanism. A new warc file is used
whenever a new connection is made or after a set duration.

Because of the streaming nature, related content (e.g., images) cannot be fetched at the same time as the tweets. This
will need to be added as a post-processing step.
"""
#TODO: Add warcinfo record

log = logging.getLogger(__name__)


class StreamDecorator(Stream):
    """
    Decorates Stream to allow url and injects SessionDecorator.
    """
    def __init__(self, auth, listener, **options):
        Stream.__init__(self, auth, listener, **options)
        self.update_listener()

    def __setattr__(self, attr, value):
        if attr == 'session':
            self.__dict__['session'] = SessionDecorator()
            self.update_listener()
        else:
            self.__dict__[attr] = value
            if attr in ['host', 'url'] and self.host and self.url:
                log.debug("Setting url on listener")
                self.listener.url = "https://%s%s" % (self.host, self.url)

    def update_listener(self):
        if self.listener:
            log.debug("Setting session on listener.")
            self.listener.session = self.session


class SessionDecorator(requests.Session, HttpLibMixin):
    def __init__(self):
        requests.Session.__init__(self)
        self.http_headers = []

    def request(self, *args, **kwargs):
        resp, capture_out = self.wrap_execute(
            lambda: requests.Session.request(self, *args, **kwargs),
            http_client.HTTPConnection)
        self.http_headers = self.parse_capture(capture_out)

        return resp


class WarcListener(StreamListener, HttpLibMixin):
    """
    A listener which writes data to a rotating warc file.
    """
    def __init__(self, collection, stream_name, data_dir, seed=False, duration_minutes=15, tweets_per_record=25000):
        StreamListener.__init__(self)
        log.info("Streaming %s tweets for %s collection into %s. Rotating files every %s minutes. Rotating "
                 "records every %s tweets",
                 stream_name, collection, data_dir, duration_minutes, tweets_per_record)
        self.collection = collection
        self.stream_name = stream_name
        self.duration_minutes = duration_minutes
        self.tweets_per_record = tweets_per_record
        self.data_dir = data_dir
        self.seed = seed

        #Create data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        self.period_start = None
        self.period_start_time = None
        self.warc = None
        self.warc_filepath = None
        self.segment_origin_id = None
        self.payload = ""
        self.segment = 1
        self.segment_total_length = 0
        self.tweet_count = 0
        #These will be set by StreamDecorator
        self.session = None
        self.url = None

    def on_data(self, data):
        #See if rotating file necessary
        if time.time() - self.period_start_time > (self.duration_minutes * 60):
            log.debug("Rotating file")
            self.close_warc()
            self.open_warc()
        elif self.tweet_count >= self.tweets_per_record:
            log.debug("Rotating record")
            self.write_warc_record()
        self.payload += data
        self.tweet_count += 1

    def on_connect(self):
        #This is called when a new connection is made.
        log.debug("Connected")
        #Close warc
        self.close_warc(end_continuation=True)
        #Open file
        self.open_warc()

    def on_error(self, status_code):
        log.error("Http error: %s", status_code)
        return False

    def on_timeout(self):
        log.warn("Timed out")
        return

    def on_disconnect(self, notice):
        log.warn("Disconnect: %s", notice)
        return

    def close_warc(self, end_continuation=False):
        if self.warc:
            self.write_warc_record(end_continuation=end_continuation)
            self.warc.close()
            self.warc = None
            if self.seed:
                #Create a symlink that will indicate that this warc should be used as a seed.
                link_dir = "%s/%s" % (self.data_dir, self.stream_name)
                if not os.path.exists(link_dir):
                    os.makedirs(link_dir)
                link_filepath = "%s/%s" % (link_dir, os.path.basename(self.warc_filepath))
                log.debug("Linking %s to %s", link_filepath, self.warc_filepath)
                os.symlink(self.warc_filepath, link_filepath)

    def open_warc(self):
        #Reset period
        self.period_start = time.gmtime()
        self.period_start_time = time.time()

        #Open the warc
        self.warc_filepath = utilities.generate_warc_filepath(self.data_dir, self.collection, type=self.stream_name)
        utilities.create_warc_dir(self.warc_filepath)
        log.debug("Opening %s", self.warc_filepath)
        self.warc = warc.open(self.warc_filepath, "wb")

    def write_warc_record(self, end_continuation=False):
        if self.payload != "":
            self.segment_total_length += len(self.payload)
            headers = {}
            if self.segment == 1:
                #Write request and response
                assert len(self.session.http_headers) == 2
                #Write request
                self.warc.write_record(self.to_warc_record("request", self.url,
                                                           http_header=self.session.http_headers[0]))
                #Write response
                if not end_continuation:
                    headers["WARC-Segment-Number"] = str(self.segment)
                warc_record = self.to_warc_record("response", self.url, http_body=self.payload,
                                                  http_header=self.session.http_headers[1],
                                                  headers=headers)
                self.warc.write_record(warc_record)
                self.segment_origin_id = warc_record.header.record_id
            else:
                #Add the length to segment total length
                headers["WARC-Segment-Origin-ID"] = self.segment_origin_id
                headers["WARC-Segment-Number"] = str(self.segment)
                if end_continuation:
                    headers["WARC-Segment-Total-Length"] = str(self.segment_total_length)
                self.warc.write_record(
                    self.to_warc_record("continuation", self.url, http_body=self.payload, headers=headers))
            log.info("Wrote segment %s to %s",
                     self.segment, self.warc_filepath)
            self.segment += 1

        #Reset
        self.payload = ""
        self.tweet_count = 0
        if end_continuation:
            self.segment_total_length = 0
            self.segment = 1

    #Methods to make this a Context Manager. This is necessary to make sure the warc record is closed properly.
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_warc(end_continuation=True)

def execute(collection, stream_name, data_path, stream_config):
    auth = OAuthHandler(config.twitter_consumer_key, config.twitter_consumer_secret)
    auth.set_access_token(config.twitter_access_token, config.twitter_access_token_secret)

    #with makes sure that warc record is properly ended
    with WarcListener(collection, stream_name, data_path,
                      seed=stream_config.get("seed", False),
                      duration_minutes=config.twitter_duration_minutes,
                      tweets_per_record=config.twitter_tweets_per_record) as l:
        stream = StreamDecorator(auth, l)
        if stream_config["type"] == "sample":
            languages = stream_config.get("languages", None)
            log.info("Running sample stream. Languages=%s.", languages)
            stream.sample(languages=languages)
        elif stream_config["type"] == "filter":
            follow = None
            if "follow" in stream_config:
                follow = []
                screen_names = []
                for u in stream_config["follow"]:
                    if isinstance(u, int):
                        #User_id
                        follow.append(str(u))
                    else:
                        #screen name
                        screen_names.append(u)
                if screen_names:
                    result = twitter.lookup_user_ids(screen_names)
                    follow.extend([str(f) for f in result.values()])
            track=stream_config.get("track", None)
            log.info("Running filter stream. Follow=%s. Track=%s.", follow, track)
            stream.filter(follow=follow, track=track)


if __name__ == '__main__':
    #Logging
    log.setLevel(logging.INFO)
    log.addHandler(logging.StreamHandler())

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("stream_name")
    parser_args = parser.parse_args()

    #TODO: This should be configurable
    import collection_config

    execute(collection_config.collection, parser_args.stream_name,
            collection_config.data_path, collection_config.streams[parser_args.stream_name])
