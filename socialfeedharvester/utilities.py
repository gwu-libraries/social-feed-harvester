import warc
import sys
import StringIO
import time
import os

class HttpLibMixin():
    def wrap_execute(self, exec_func, debuggable):
        #List of responses. Due to redirects, there may be multiple responses.
        resps = []

        #TODO: Check if there is an etag
        #When debuglevel is set httplib outputs details to stdout.
        #This captures stdout.
        capture_out = StringIO.StringIO()
        sys.stdout = capture_out
        #sys.stdout = Tee([capture_out, sys.__stdout__])
        debuggable.debuglevel = 1
        try:
            return_values = exec_func()
        finally:
            #Stop capturing stdout
            sys.stdout = sys.__stdout__
            debuggable.debuglevel = 0
        return return_values, capture_out

    def parse_capture(self, capture_out):
        http_headers = []
        #Reset to the beginning of capture_out
        capture_out.seek(0)
        response_header = None
        for line in capture_out:
            if line.startswith("send:"):
                #Push last req and resp
                if response_header:
                    #Response record
                    http_headers.append(response_header)
                    response_header = None
                start = line.find("GET")
                if start == -1:
                    start = line.find("POST")
                assert start != -1
                request_header = line[start:-2].replace("\\r\\n", "\r\n")
                #Request record
                http_headers.append(request_header)
            elif line.startswith("reply:"):
                #Start of the response header
                response_header = line[8:-6] + "\r\n"
            elif line.startswith("header:"):
                #Append additional headers to response header
                response_header += line[8:-2] + "\r\n"
        #Push the last response
        http_headers.append(response_header)

        return http_headers

    def to_warc_records(self, capture_out, resps):
        http_headers = self.parse_capture(capture_out)
        warc_records = []
        response_counter = 0
        counter = 0
        for (counter, http_header) in enumerate(http_headers):
            if counter % 2 == 0:
                #Request record
                warc_records.append(self.to_warc_record("request", resps[response_counter].url,
                                                        http_header))
            else:
                #Response record
                warc_records.append(self.to_warc_record("response", resps[response_counter].url,
                                                        http_header, http_body=resps[response_counter].content,
                                                        concurrent_to_warc_record=warc_records[-1]))
                response_counter += 1

        return warc_records

    def to_warc_record(self, warc_type, url, http_header=None, http_body=None, concurrent_to_warc_record=None,
                       headers=None):
        warc_headers = {
            "WARC-Target-Target-URI": url,
            "WARC-Type": warc_type
        }
        if headers:
            warc_headers.update(headers)
        if concurrent_to_warc_record:
            warc_headers["WARC-Concurrent-To"] = concurrent_to_warc_record.header.record_id
        payload = None
        if http_header:
            payload = http_header
        if http_body:
                if payload:
                    payload += "\r\n" + http_body
                else:
                    payload = http_body

        return warc.WARCRecord(payload=payload, headers=warc_headers)


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


def generate_warc_filepath(data_path, collection, type=None):
    t = time.gmtime()
    name = collection
    if type:
        name += "-" + type
    return "%s/%s/%s/%s/%s/%s-%s.warc.gz" % (
            data_path,
            time.strftime('%Y', t),
            time.strftime('%m', t),
            time.strftime('%d', t),
            time.strftime('%H', t),
            name,
            time.strftime('%Y-%m-%dT%H:%M:%SZ', t)
        )


def create_warc_dir(warc_filepath):
    #Create the directory
    warc_dir = os.path.dirname(warc_filepath)
    if not os.path.exists(warc_dir):
        os.makedirs(warc_dir)
