
"""
Support for parsing and writing files in OpenRCV's internal format.

"""

from contextlib import contextmanager
import os

from openrcv.formats.common import Format, FormatWriter
from openrcv.streams import StreamResourceBase
from openrcv.utils import join_values, FileWriter


# ASCII makes reading and parsing the file faster.
ENCODING_BALLOT_FILE = 'ascii'


def to_internal_ballot(ballot):
    """Return the ballot as an internal ballot string."""
    # There is no terminal 0 like in the BLT format.
    weight, choices = ballot
    return join_values([weight] + list(choices))


class _WriteableBallotStream(object):

    def __init__(self, stream):
        self.stream = stream

    def write(self, ballot):
        line = to_internal_ballot(ballot)
        self.stream.write(line + "\n")


class InternalBallotsResource(StreamResourceBase):

    label = "ballot"

    def __init__(self, resource):
        """
        Arguments:
          resource: backing store for the resource.
        """
        self.resource = resource

    @contextmanager
    def open_read(self):
        """Return an iterator object."""
        yield iter(self.seq)

    @contextmanager
    def open_write(self):
        with self.resource.writing() as stream:
            yield _WriteableBallotStream(stream)


class InternalFormat(Format):

    @property
    def contest_writer_cls(self):
        return InternalContestWriter


# TODO: DRY up with BLTContestWriter.
class InternalContestWriter(FormatWriter):

    @property
    def file_info_funcs(self):
        return (self.get_output_info, )

    def get_output_info(self, output_dir):
        return os.path.join(self.output_dir, "ballots.txt"), ENCODING_BALLOT_FILE

    def resource_write(self, resource, contest):
        writer = InternalBallotsWriter(resource)
        writer.write_ballots(contest)


class InternalBallotsWriter(FileWriter):

    def _write_ballots(self, contest):
        with contest.ballots_resource() as ballots:
            for ballot in ballots:
                self.writeln(to_internal_ballot(ballot))

    def write_ballots(self, contest):
        """
        Arguments:
          contest: a ContestInput object.
        """
        with self.open():
            self._write_ballots(contest)
