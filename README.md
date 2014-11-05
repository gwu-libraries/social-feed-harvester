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

sfh
---
sfh will harvest the seeds specified in `collection_config.py`.

twh
---
twh will harvest from the Twitter Streaming API.  Streams are specified in `collection_config.py`.

The stream name must be provided as an argument.  For example:
```
python twh.py sample
```