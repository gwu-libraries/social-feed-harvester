from __future__ import absolute_import
import warc as ia_warc
import sys
import StringIO

class ClientManager():
    """
    Keeps track of social media service client/api objects.
    """
    def __init__(self, create_client_func):
        """
        :param create_client_func: A function that will create a client/api object. It should accept the necessary
        arguments to construct the object.
        """
        self._clients = {}
        self.create_client_func=create_client_func

    def get_client(self, *args, **kwargs):
        """
        Returns a client/api object either by constructing a new one or returning one which is previously created.

        Should be invoked with the same arguments expected by the create_client_func.
        """
        key = "client" + ".".join((str(v) for v in args)) + ".".join((str(v) for v in kwargs.values()))
        if key not in self._clients:
            self._clients[key] = self.create_client_func(*args, **kwargs)
        return self._clients[key]


class HttpLibMixin():
    def wrap_execute(self, exec_func, debuggable):
        """
        Enables debugging on debuggable, calls an API function, and captures output.
        :param exec_func: the API function.
        :param debuggable: the http client that debug is to be set on.
        :return: results of the function, captured stdout as a StringIO.
        """

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
        """
        Transform the captured stdout into a series of request and response headers
        """

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

    def parse_url(self, http_header):
        """
        Parse the url from the http request header.

        Note that this excludes the protocol, host, and port.
        """
        assert http_header.startswith("GET")
        end_pos = http_header.find(" HTTP/")
        assert end_pos != -1
        return http_header[4:end_pos]


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

        return ia_warc.WARCRecord(payload=payload, headers=warc_headers)
