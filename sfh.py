from collections import deque
import logging
import time

import warc
import os
from socialfeedharvester.tumblr import Blog
from socialfeedharvester.twitter import TweetWarc, UserTimeline
from socialfeedharvester.resource import Resource
from config import wait
import codecs
import json
import socialfeedharvester.utilities as utilities

log = logging.getLogger("socialfeedharvester")


class SocialFeedHarvester():
    def __init__(self, collection, data_path, seeds):
        self.data_path = data_path
        self.warc_filepath = utilities.generate_warc_filepath(data_path, collection)

        #Declare queue
        #TODO:  This should be serialized to disk.
        self._queue = deque()

        #Load state.  State is what has already been processed from a feed.
        self.state_filepath = os.path.join(data_path, "state.json")
        if os.path.exists(self.state_filepath):
            log.debug("Loading state from %s", self.state_filepath)
            with codecs.open(self.state_filepath, "r") as state_file:
                self._state = json.load(state_file)
        else:
            self._state = {}

        #Fetched is list of urls that have already been fetched.
        #For now this will only be items fetched in this process, but for deduping should extend across the
        #entire collection and use some combination of etags and fixities.
        self._fetched = []

        #Queue based on seeds
        for seed in seeds:
            seed_type = seed["type"]
            #Remove type from seed
            del seed["type"]
            if seed_type == "blog":
                self.queue_blog(**seed)
            elif seed_type == "stream":
                self.queue_stream(**seed)
            elif seed_type == "resource":
                self.queue_resource(**seed)
            elif seed_type == "user_timeline":
                self.queue_user_timeline(**seed)

    def queue_blog(self, blog_name, max_posts=None):
        """
        Queue a blog to be fetched.

        :param blog_name: name of the blog. Blog short name is fine (e.g., foo instead of foo.tumblr.com).
        :param max_posts: the maximum number of posts to fetch.  Default is all.  For testing only.
        """
        #Note that API does not support any mechanism only getting the posts since last fetch.  There is no posted-since
        #limit and offset isn't guaranteed to be consistent across time.
        blog = Blog(blog_name, max_posts, self)
        log.debug("Queueing %s.", blog)
        self.queue_append(blog)

    def queue_stream(self, name):
        stream_dir = "%s/%s" % (self.data_path, name)
        for w in os.listdir(stream_dir):
            tweet_warc = TweetWarc("%s/%s" % (stream_dir, w), self)
            log.debug("Queueing %s.", tweet_warc)
            self.queue_append(tweet_warc)

    def queue_resource(self, url):
        resource = Resource(url, self)
        log.debug("Queueing %s.", resource)
        self.queue_append(resource)

    def queue_user_timeline(self, screen_name):
        user_timeline = UserTimeline(screen_name=screen_name)
        log.debug("Queueing %s.", user_timeline)
        self.queue_append(user_timeline)

    def queue_append(self, fetchable):
        """
        Add a fetchable to the end of the queue.
        """
        log.debug("Appending %s to queue.", fetchable)
        self._queue.append(fetchable)

    def queue_appendleft(self, fetchable):
        """
        Add a fetchable to the start of the queue.
        """
        log.debug("Prepending %s to queue.", fetchable)
        self._queue.appendleft(fetchable)

    def queue_extendleft(self, fetchables):
        """
        Add fetchables to the start of the queue.
        """
        for fetchable in fetchables:
            self.queue_appendleft(fetchable)

    def queue_extend(self, fetchables):
        """
        Add fetchables to the end of the queue.
        """
        for fetchable in fetchables:
            self.queue_append(fetchable)

    def fetch(self, dry_run=False, exclude_fetch=None):
        """
        Perform the fetch.

        :param dry_run: fetch, but don't write to warc.
        :param exclude_fetch: list of class names of fetchables to exclude.
        """
        if exclude_fetch is None:
            exclude_fetch = []

        log.info("Starting fetch. Dry run=%s. Excludes=%s.", dry_run, exclude_fetch)

        warc_file = None
        if not dry_run:
            log.info("Writing to %s", self.warc_filepath)
            #Create the directory
            utilities.create_warc_dir(self.warc_filepath)
            #Open warc
            warc_file = warc.open(self.warc_filepath, "w")

        try:
            while self._queue:
                fetchable = self._queue.popleft()
                if fetchable.__class__.__name__ not in exclude_fetch:
                    if fetchable.is_fetchable:
                        log.debug("Fetching %s", fetchable)
                        warc_records = fetchable.fetch()
                        if warc_records:
                            for warc_record in warc_records:
                                if warc_file:
                                    log.debug("Writing %s", fetchable)
                                    warc_file.write_record(warc_record)
                                #Add to fetched.
                                if "WARC-Target-URI" in warc_record.header:
                                    self._fetched.append(warc_record.header["WARC-Target-URI"])
                        time.sleep(wait)
                    else:
                        log.debug("%s not fetchable", fetchable)
                else:
                    log.debug("Not fetching %s", fetchable)
        finally:
            if not dry_run:
                warc_file.close()
        log.info("Fetching complete.")

        #Save state
        if self._state:
            if not dry_run:
                log.debug("Dumping state to %s", self.state_filepath)
                with codecs.open(self.state_filepath, 'w') as state_file:
                    json.dump(self._state, state_file)
            else:
                log.debug("State: %s", self._state)

    def get_state(self, resource_type, key):
        if resource_type in self._state and key in self._state[resource_type]:
            return self._state[resource_type][key]
        else:
            return None

    def set_state(self, resource_type, key, value):
        log.debug("Setting state for %s with key %s to %s", resource_type, key, value)
        if value is not None:
            if resource_type not in self._state:
                self._state[resource_type] = {}
            self._state[resource_type][key] = value
        else:
            #Clearing value
            if resource_type in self._state and key in self._state[resource_type]:
                #Delete key
                del self._state[resource_type][key]
                #If resource type is empty then delete
                if not self._state[resource_type]:
                    del self._state[resource_type]

    def is_fetched(self, url):
        return url in self._fetched

    def set_fetched(self, url):
        if url not in self._fetched:
            self._fetched.append(url)

if __name__ == '__main__':
    #Logging
    log.setLevel(logging.DEBUG)
    log.addHandler(logging.StreamHandler())


    #Import seeds.
    #TODO: This should be configurable.
    import collection_config

    sfh = SocialFeedHarvester(collection_config.collection, collection_config.data_path, collection_config.seeds)
    sfh.fetch(dry_run=collection_config.dry_run, exclude_fetch=collection_config.exclude_fetch)