#The name of the collection being harvested.
collection = "test"
#The location to put the collection.
data_path = "/tmp/test_crawl"
#If True, will not write the collected fetchables to WARC.
dry_run=False
#Types of fetchables to exclude from fetching.
#exclude_fetch=["Image", "Html", "UnknownResource"]
exclude_fetch=[]
seeds = [
    #A Twitter user timeline seed
    {
        "type": "user_timeline",
        "screen_name": "justin_littman"
    },
    #A Tumblr blog seed
    # {
    #    "type": "blog",
    #    "blog_name": "libraryjournal",
    #    # "max_posts": 20
    # },
    #Use warcs from this stream as seeds for further fetching.
    # {
    #     "type": "stream",
    #     "name": "libs"
    # },
    #A resource
    # {
    #     "type": "resource",
    #     "url": "http://bit.ly/A9Q3zb"
    # },
]
streams = {
    "sample": {
        "type": "sample",
        "languages": ["en"],
        #Use this as a seed for further fetching.
        "seed": False
    },
    "libs": {
        "type": "filter",
        #screen names or user ids
        "follow": [101802390,
                   "britishlibrary",
                   "librarycongress",
                   "gelmanlibrary"],
        "track": ["library"],
        "seed": True
    }
}
