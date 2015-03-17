import flickrapi
import logging
import httplib as http_client
import json

from socialfeedharvester.fetchables.utilities import ClientManager, HttpLibMixin
from socialfeedharvester.fetchables.resource import Image

log = logging.getLogger(__name__)

FLICKR_HOST = "https://api.flickr.com"


class User(HttpLibMixin):
    is_fetchable = True

    def __init__(self, sfh, username=None, nsid=None, incremental=True, per_page=None):
        self.sfh = sfh
        assert username or nsid
        self.username = username
        self.nsid = nsid
        self.incremental = incremental
        self.api = get_api(self.sfh)
        #Per_page is intended for testing purposes only.
        self.per_page = per_page

    def fetch(self):
        #Lookup nsid if don't already know
        if not self.nsid:
            log.debug("Looking up nsid for %s", self.username)
            self.nsid = lookup_nsid(self.username, self.api)
            if not self.nsid:
                #TODO:  How do we want to handle exceptions?
                raise Exception("Could not find nsid for %s" % self.username)

        warc_records = []
        fetchables = []

        #TODO:  Only fetch incremental
        #Get info on the user
        #Setting format=json will return raw json.
        raw_json_resp, capture_out = self.wrap_execute(
            lambda: self.api.people.getInfo(user_id=self.nsid, format='json'),
            http_client.HTTPConnection)
        http_headers = self.parse_capture(capture_out)
        #Write request and response
        assert len(http_headers) == 2
        url = FLICKR_HOST + self.parse_url(http_headers[0])

        #Write request
        warc_records.append((self.to_warc_record("request", url,
                                                   http_header=http_headers[0])))
        #Write response
        warc_records.append(self.to_warc_record("response", url, http_body=raw_json_resp,
                                          http_header=http_headers[1]))

        #Get first page of public photos to get number of pages and photos
        json_resp = self.api.people.getPublicPhotos(user_id=self.nsid, format='parsed-json', per_page=self.per_page)
        total_pages = json_resp["photos"]["pages"]

        last_photo_id = self.sfh.get_state(__name__, "%s.last_photo_id" % self.nsid) if self.incremental else False
        new_last_photo_id = None
        found_last_photo_id = False
        #Going through pages backward
        for page in reversed(range(1,total_pages+1)):
            log.debug("Fetching %s of %s pages.", page, total_pages)
            raw_json_resp, capture_out = self.wrap_execute(
                lambda: self.api.people.getPublicPhotos(user_id=self.nsid, format='json',
                                                        per_page=self.per_page, page=page), http_client.HTTPConnection)
            http_headers = self.parse_capture(capture_out)

            json_resp = json.loads(raw_json_resp)
            #print json.dumps(json_resp, indent=4)
            #Going through photos backwards
            added_fetchables = False
            for photo in reversed(json_resp["photos"]["photo"]):
                photo_id = photo["id"]
                if new_last_photo_id is None and photo_id != last_photo_id:
                    new_last_photo_id = photo_id
                log.debug("Photo %s" % photo_id)
                if photo_id == last_photo_id:
                    log.debug("Is last photo")
                    found_last_photo_id = True
                    break
                added_fetchables = True
                fetchables.append(Photo(photo["id"], photo["secret"], self.sfh))

            if added_fetchables:
                log.debug("Added fetchables for this page, so writing request and response")
                #Write request and response
                assert len(http_headers) == 2
                url = FLICKR_HOST + self.parse_url(http_headers[0])

                #Write request
                warc_records.append((self.to_warc_record("request", url,
                                                           http_header=http_headers[0])))
                #Write response
                warc_records.append(self.to_warc_record("response", url, http_body=raw_json_resp,
                                                  http_header=http_headers[1]))
            if found_last_photo_id:
                break


        if new_last_photo_id:
            log.debug("New last photo id is %s", new_last_photo_id)
            self.sfh.set_state(__name__, "%s.last_photo_id" % self.nsid, new_last_photo_id)

        return warc_records, fetchables

    def __str__(self):
        return "flickr user %s" % self.nsid


class Photo(HttpLibMixin):
    is_fetchable = True

    def __init__(self, photo_id, secret, sfh, sizes=("Thumbnail", "Large", "Original")):
        self.sfh = sfh
        self.photo_id = photo_id
        self.secret = secret
        self.api = get_api(self.sfh)
        self.sizes = sizes

    def fetch(self):
        #Get info for photo
        warc_records = []
        fetchables = []

        #Get info on the user
        #Setting format=json will return raw json.
        raw_json_resp, capture_out = self.wrap_execute(
            lambda: self.api.photos.getInfo(photo_id=self.photo_id, secret=self.secret, format='json'),
            http_client.HTTPConnection)
        http_headers = self.parse_capture(capture_out)
        #Write request and response
        assert len(http_headers) == 2
        url = FLICKR_HOST + self.parse_url(http_headers[0])

        #Write request
        warc_records.append((self.to_warc_record("request", url,
                                                   http_header=http_headers[0])))
        #Write response
        warc_records.append(self.to_warc_record("response", url, http_body=raw_json_resp,
                                          http_header=http_headers[1]))

        #Call getSizes, but don't record
        sizes_json_resp = self.api.photos.getSizes(photo_id=self.photo_id, format='parsed-json')
        print json.dumps(sizes_json_resp, indent=4)
        for size in sizes_json_resp["sizes"]["size"]:
            if size["label"] in self.sizes:
                log.debug("Creating fetchable for %s", size["label"])
                fetchables.append(Image(size["source"], self.sfh))
            else:
                log.debug("Skipping fetchable for %s", size["label"])

        #json_resp = json.loads(raw_json_resp)
        #print json.dumps(json_resp, indent=4)
        return warc_records, fetchables

def lookup_nsid(username, api):
    """
    Lookup a user's nsid.
    :param username: Username to lookup.
    :param api: A configured Flickr api.
    :return: The nsid or None if not found.
    """
    resp = api.people.findByUsername(username=username, format="parsed-json")
    nsid = None
    if resp["stat"] == "ok":
        nsid = resp["user"]["nsid"]
    log.debug("Looking up username %s returned %s", username, nsid)
    return nsid

def create_flickr_client(key, secret):
    return flickrapi.FlickrAPI(key, secret, store_token=False)

client_manager = ClientManager(create_flickr_client)


def get_api(sfh):
    auth = sfh.get_auth("flickr")
    return client_manager.get_client(auth["key"], auth["secret"])