from __future__ import absolute_import
import logging
import os
import warc as ia_warc

log = logging.getLogger(__name__)

"""
A warc record writer persists warc records.  How those warc records are persisted depends on the implementation.

A warc record writer should implement the signature of WarcWriter.  close() should be called when the warc record writer
is no longer needed.
"""


class WarcWriter():
    """
    A warc record writer that writes to a WARC file using the warc library.
    """
    def __init__(self, filepath):
        """
        :param filepath:  The filepath of the WARC file.
        """
        self.filepath = filepath
        log.info("Writing to %s", self.filepath)

        #Create the directory
        filepath_parent = os.path.dirname(self.filepath)
        if not os.path.exists(filepath_parent):
            log.debug("Creating %s directory.", filepath_parent)
            os.makedirs(filepath_parent)

        #Open warc
        self._warc_file = ia_warc.open(self.filepath, "w")

    def close(self):
        log.debug("Closing %s.", self.filepath)
        self._warc_file.close()

    def write_record(self, warc_record):
        """
        :param warc_record:  The warc record to be written.  Should be type compatible with WARCRecord in the warc library.
        """
        self._warc_file.write_record(warc_record)


class DryRunWarcWriter():
    """
    A warc record writer for dry runs.
    """
    def __init__(self):
        pass

    def close(self):
        pass

    def write_record(self, warc_record):
        pass
