from __future__ import absolute_import
from tests import TestCase
import tempfile
import os
import socialfeedharvester.warc as sfh_warc
import warc as ia_warc


class TestWarcWriter(TestCase):

    def setUp(self):
        self.warc_filepath = os.path.join(tempfile.mkdtemp(), "test.warc")
        self.warc_writer = sfh_warc.WarcWriter(self.warc_filepath)

    def test_write(self):
        record = ia_warc.WARCRecord(payload="helloworld", headers={"WARC-Type": "response"})
        self.warc_writer.write_record(record)
        self.warc_writer.close()

        #Now read it back
        f = ia_warc.WARCFile(filename=self.warc_filepath)
        count = 0
        for r in f:
            count += 1
            self.assertEqual("response", r["WARC-Type"], "WARC-Type is not response.")
            self.assertEqual("helloworld", r.payload.read(), "Payload is not correct.")
        self.assertEqual(1, count, "WARC file does not contain 1 record.")