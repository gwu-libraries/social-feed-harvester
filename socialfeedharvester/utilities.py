import time
import os


class HttLib2ResponseAdapter():
    """
    Adapts a httplib2.Response to be more like an httplib.HttpResponse.
    """
    def __init__(self, response, content):
        self.response = response
        self.url = response["content-location"]
        self.content = content


class Tee(object):
    """
    Tees output to multiple file-like objects.

    Useful for testing capture of httplib output.
    """
    def __init__(self, outs):
        self.outs = outs

    def write(self, data):
        map(lambda out: out.write(data), self.outs)


def generate_warc_filepath(data_path, collection=None, warc_type=None):
    t = time.gmtime()
    name = collection or os.path.basename(data_path.rstrip("/"))
    if warc_type:
        name += "-" + warc_type
    return "%s/%s/%s/%s/%s/%s-%s.warc.gz" % (
        data_path,
        time.strftime('%Y', t),
        time.strftime('%m', t),
        time.strftime('%d', t),
        time.strftime('%H', t),
        name,
        time.strftime('%Y-%m-%dT%H:%M:%SZ', t)
    )
