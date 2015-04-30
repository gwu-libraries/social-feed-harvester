import logging
import time
import os
import argparse
import json
from socialfeedharvester.fetchables.tumblr import Blog
from socialfeedharvester.fetchables.twitter import TweetWarc, UserTimeline
from socialfeedharvester.fetchables.flickr import User
from socialfeedharvester.fetchables.resource import Resource, UnknownResource
from config import wait
from socialfeedharvester.fetchable_queue import FetchableDeque
from socialfeedharvester.harvest_state_store import DictHarvestStateStore, JsonHarvestStateStore
from socialfeedharvester.fetch_strategy import DefaultFetchStrategy
from socialfeedharvester.warc import DryRunWarcWriter, WarcWriter
import socialfeedharvester.utilities as utilities


log = logging.getLogger("socialfeedharvester")


class SocialFeedHarvester():
    def __init__(self, seeds, auths=None,
                 fetchable_queue=None, harvest_state_store=None, fetch_strategy=None, warc_writer=None):
        #Queue
        if fetchable_queue:
            self._fetchable_queue = fetchable_queue
        else:
            log.debug("No fetchable queue provided so using FetchableDeque.")
            self._fetchable_queue = FetchableDeque()

        #Harvest state store
        if harvest_state_store:
            self._harvest_state_store = harvest_state_store
        else:
            log.debug("No harvest store provided so using DictHarvestStateStore.")
            self._harvest_state_store = DictHarvestStateStore()
            # self._harvest_state_store = JsonHarvestStateStore(data_path)
            
        #Fetch strategy
        if fetch_strategy:
            self._fetch_strategy = fetch_strategy
        else:
            log.debug("No fetchable strategy provided so using DefaultFetchStrategy.")
            self._fetch_strategy = DefaultFetchStrategy()

        #Warc writer
        if warc_writer:
            self._warc_writer = warc_writer
        else:
            log.debug("No warc writer provided so using a DryRunWarcWriter")
            self._warc_writer = DryRunWarcWriter()

        #Fetched is list of urls that have already been fetched in this harvest.
        self._fetched = []

        #Auths
        self._auths = auths or {}

        #Queue based on seeds
        for seed in seeds:
            seed_type = seed["type"]
            #Remove type from seed
            del seed["type"]
            if seed_type == "tumblr_blog":
                self.queue_tumblr_blog(**seed)
            elif seed_type == "twitter_stream":
                self.queue_twitter_stream(**seed)
            elif seed_type == "resource":
                self.queue_resource(**seed)
            elif seed_type == "twitter_user_timeline":
                self.queue_twitter_user_timeline(**seed)
            elif seed_type == "flickr_user":
                self.queue_flickr_user(**seed)
            else:
                log.warn("Unknown seed type: %s", seed_type)

    def queue_tumblr_blog(self, blog_name, incremental=True, max_posts=None):
        """
        Queue a blog to be fetched.

        :param blog_name: name of the blog. Blog short name is fine (e.g., foo instead of foo.tumblr.com).
        :param incremental:  If True, only fetch posts new posts for the blog.  Otherwise, fetch all posts.
        """
        #Note that API does not support any mechanism only getting the posts since last fetch.  There is no posted-since
        #limit and offset isn't guaranteed to be consistent across time.
        blog = Blog(blog_name, self, incremental=incremental)
        log.debug("Queueing %s.", blog)
        self._queue_fetchables(blog)

    def queue_twitter_stream(self, name):
        stream_dir = "%s/%s" % (self.data_path, name)
        for w in os.listdir(stream_dir):
            tweet_warc = TweetWarc("%s/%s" % (stream_dir, w), self)
            log.debug("Queueing %s.", tweet_warc)
            self._queue_fetchables(tweet_warc)

    def queue_resource(self, url):
        resource = Resource(url, self)
        log.debug("Queueing %s.", resource)
        self._queue_fetchables(resource)

    def queue_twitter_user_timeline(self, screen_name):
        user_timeline = UserTimeline(self, screen_name=screen_name)
        log.debug("Queueing %s.", user_timeline)
        self._queue_fetchables(user_timeline)

    def queue_flickr_user(self, username=None, nsid=None):
        user = User(self, username=username, nsid=nsid)
        log.debug("Queueing %s.", user)
        self._queue_fetchables(user)


    def _queue_fetchables(self, fetchables, depth=1):
        """
        Add a fetchable or list of fetchables to the queue.
        """
        self._fetchable_queue.add(fetchables, depth)

    def fetch(self):
        """
        Perform the fetch.
        """
        log.info("Starting fetch.")

        try:
            for (fetchable, depth) in ((f, d) for (f, d) in self._fetchable_queue
                                       if self._fetch_strategy.fetch_decision(f, d)):
                    log.debug("Fetching %s (depth %s)", fetchable, depth)
                    (warc_records, linked_fetchables) = fetchable.fetch()
                    if linked_fetchables:
                        #Depth incremented except for linked fetchables from UnknownResources
                        self._queue_fetchables(linked_fetchables, depth+1 if not isinstance(fetchable, UnknownResource) else depth)
                    if warc_records:
                        for warc_record in warc_records:
                            log.debug("Writing %s for %s", warc_record.type, fetchable)
                            self._warc_writer.write_record(warc_record)
                            #Add to fetched.
                            if "WARC-Target-URI" in warc_record.header:
                                self._fetched.append(warc_record.header["WARC-Target-URI"])
                    time.sleep(wait)
        finally:
            self._warc_writer.close()
        log.info("Fetching complete.")

        #Save state
        self._harvest_state_store.close()

    def get_state(self, resource_type, key):
        """
        Get the state of a harvest for a resource from harvest state store.
        """
        return self._harvest_state_store.get_state(resource_type, key)

    def set_state(self, resource_type, key, value):
        """
        Set the state of a harvest for a resource in harvest state store.
        """
        self._harvest_state_store.set_state(resource_type, key, value)

    def is_fetched(self, url):
        """
        Returns True if the URL has already been fetched in this harvest.
        """
        return url in self._fetched

    def set_fetched(self, url):
        """
        Adds the URL to the list of URLs that have been fetched in this harvest.
        """
        if url not in self._fetched:
            self._fetched.append(url)

    def get_auth(self, service_name):
        """
        Get authentication information for the service if available.
        """
        return self._auths.get(service_name, {})

if __name__ == '__main__':
    #Logging
    logging.basicConfig(format='%(asctime)s: %(name)s --> %(message)s', level=logging.DEBUG)
    # log.addHandler(logging.StreamHandler())

    parser = argparse.ArgumentParser()
    parser.add_argument("collection_path", help="Filepath of the collection.")
    parser.add_argument("seed_file", help="JSON file defining seeds for this fetch.")
    parser.add_argument("--collection-name",
                        help="Name of the collection.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch, but do not persist.")
    parser.add_argument("--ignore-state", action="store_true", help="Ignore an existing persisted state.")

    args = parser.parse_args()

    #Load seeds
    with open(args.seed_file) as seed_file:
        sf = json.load(seed_file)

    ww = None
    if not args.dry_run:
        ww = WarcWriter(utilities.generate_warc_filepath(args.collection_path, args.collection_name))

    #If ignore_state, then don't load existing harvest state store.
    #If dry_run, don't persist on close.
    ss = JsonHarvestStateStore(args.collection_path, load_existing=not args.ignore_state,
                               persist_on_close=not args.dry_run)

    #Setup a fetch strategy
    fs = None
    if "fetch_strategy" in sf:
        fs = DefaultFetchStrategy(depth2_resource_types=sf["fetch_strategy"].get("depth2_resource_types"),
                                  depth3_resource_types=sf["fetch_strategy"].get("depth3_resource_types"))

    sfh = SocialFeedHarvester(sf["seeds"], auths=sf["auths"] if "auths" in sf else None,
                              warc_writer=ww, harvest_state_store=ss, fetch_strategy=fs)
    sfh.fetch()
