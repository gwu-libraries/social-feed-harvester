social-feed-harvester
=====================

A proof-of-concept for harvesting social media and other web resources to WARC files.

Configuration
-------------
1. Create a virtual environment:

    ```
    virtualenv ENV
    source ENV/bin/activate
    ```
2. Install requirements:

    ```
    pip install -r requirements.txt
    ```
3. Make a local copy of `config.py`:

    ```
    cp sample_config.py config.py
    ```
    At this point, there are no values you should need to change in this file.
    
4. Make a copy of `sample_seeds`:
    
    ```
    cp -r sample_seeds seeds
    ```
    Make changes in the seed files (or create additional) as appropriate.  _You must provide correct Twitter, Flickr, and Tumblr api credentials._


sfh
---
sfh will harvest Twitter, Flickr, and Tumblr data.  It can be invoked with:

```
python sfh.py <collection path> <seed file>
```

For example:
```
python sfh.py /collections/my_collection seeds/flickr_seeds.json
```

twh
---
twh will harvest from the Twitter Streaming API.  __It is currently broken.__