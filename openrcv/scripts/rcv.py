
"""
Supports the "rcv" command-line command (aka console_script).

"""

import argparse
from argparse import RawDescriptionHelpFormatter
import logging
from textwrap import dedent

from openrcv.scripts.argparse import (parse_log_level, ArgParser, HelpAction,
                                      HelpRequested, Option, UsageException)
from openrcv.formats.blt import BLTFormat
from openrcv.formats.internal import InternalFormat
from openrcv.formats.jscase import JsonCaseFormat
from openrcv.scripts import commands
from openrcv.scripts.run import main as _main
from openrcv import utils


# For increased compatibility (specifically with Python 3.4 <= 3.4.1),
# we rely primarily on the log level number rather than the string name.
# This is because in Python 3.4 (but fixed in 3.4.2), you could not use
# logging.getLevelName() to obtain the level number from a level name.
# Travis CI was using 3.4.1 as of Oct. 26, 2014.  For more info, see--
#   http://bugs.python.org/issue22386"
LOG_LEVEL_DEFAULT = 20  # corresponds to INFO.
LOG_LEVEL_DEFAULT_NAME = logging.getLevelName(LOG_LEVEL_DEFAULT)
# The log level that should be used if the ArgumentParser raises a UsageException.
LOG_LEVEL_USAGE_ERROR = 20  # corresponds to INFO.

DESCRIPTION = """\
OpenRCV command-line tool.

"""

OPTION_HELP = Option(('-h', '--help'))
OPTION_OUTPUT_DIR = Option(('-o', '--output-dir'), "OUTPUT_DIR")
OPTION_OUTPUT_FORMAT = Option(('-f', '--output-format'), "OUTPUT_FORMAT")

OUTPUT_FORMAT_BLT = 'blt'
OUTPUT_FORMAT_INTERNAL = 'internal'
OUTPUT_FORMAT_TEST = 'jscase'
# TODO: default to OpenRCV format.
OUTPUT_FORMAT_DEFAULT = OUTPUT_FORMAT_BLT


def main():
    parser = create_argparser()
    _main(parser)


def make_output_formats():
    formats = (
        OutputFormat(OUTPUT_FORMAT_BLT, cls=BLTFormat,
                     desc="BLT format"),
        OutputFormat(OUTPUT_FORMAT_INTERNAL, cls=InternalFormat,
                     desc="internal OpenRCV format"),
        OutputFormat(OUTPUT_FORMAT_TEST, cls=JsonCaseFormat,
                     desc="JSON test case"),
    )
    mapping = {format.label: format for format in formats}
    return mapping


def add_help(parser):
    # The add_argument() call for help is modeled after how argparse
    # does it internally.
    parser.add_argument(*OPTION_HELP, action=HelpAction,
        help='show this help message and exit.')


class CommandBase(object):

    def __init__(self, builder):
        """
        Arguments:
          builder: an ArgParserBuilder object.
        """
        self.builder = builder

    def add_arguments(self, parser):
        raise utils.NoImplementation(self)

    def add(self):
        """Add the command to subparsers."""
        subparsers = self.builder.subparsers
        parser = subparsers.add_parser(self.name, help=self.help, description=self.desc,
                                       add_help=False)
        self.add_arguments(parser)
        # The RawDescriptionHelpFormatter preserves line breaks in the
        # description and epilog strings.
        parser.formatter_class = RawDescriptionHelpFormatter
        parser.set_defaults(run_command=self.func)
        add_help(parser)


class CountCommand(CommandBase):

    name = "count"
    help = "Tally one or more contests."

    @property
    def func(self):
        return commands.count

    desc = "Tally the contests specified by the contests file at INPUT_PATH."

    def add_arguments(self, parser):
        parser.add_argument('input_path', metavar='INPUT_PATH',
            help=("path to a contests configuration file. Supported file "
                  "formats are JSON (*.json) and YAML (*.yaml or *.yml)."))


class RandContestCommand(CommandBase):

    name = "randcontest"
    help = "Create a random sample contest."

    @property
    def func(self):
        return commands.make_random_contest

    @property
    def desc(self):
        return dedent("""\
            Create a random contest.

            This command creates a contest with random ballot data and writes the
            contest to stdout in the chosen format.  If {output_dir} is provided,
            then only the paths to the output files are written to stdout.
            """.format(output_dir=OPTION_OUTPUT_DIR.metavar))

    def add_arguments(self, parser):
        default_candidates = 6
        default_ballots = 20
        builder = self.builder
        formats = builder.formats
        parser.add_argument('-c', '--candidates', dest='candidate_count', metavar='N',
                            type=int, default=default_candidates,
                            help=('number of candidates.  Defaults to {:d}.'
                                  .format(default_candidates)))
        parser.add_argument('-b', '--ballots', dest='ballot_count', metavar='N', type=int,
                           help=('number of ballots.  Defaults to {:d}.'
                                 .format(default_ballots)))
        parser.add_argument('-N', '--normalize', action='store_true',
            help=("whether to normalize the list of ballots, which means "
                  "ordering them lexicographically and grouping identical "
                  "choices using weight."))
        parser.add_argument(*OPTION_OUTPUT_DIR.flags, metavar=OPTION_OUTPUT_DIR.metavar,
            help=("directory to write output files to.  If the empty string, "
                  "writes to stdout.  Defaults to the empty string."))
        # The output formats.
        labels = sorted(formats)
        list_desc = ", ".join((str(formats[label]) for label in labels))
        parser.add_argument(*OPTION_OUTPUT_FORMAT.flags, metavar=OPTION_OUTPUT_FORMAT.metavar,
            type=builder.writer_type, default=OUTPUT_FORMAT_DEFAULT,
            help=('the output format.  Choose from: {!s}. Defaults to: "{!s}".'
                  .format(list_desc, OUTPUT_FORMAT_DEFAULT)))
        parser.add_argument('-j', '--json-contests', metavar='JSON_PATH',
            dest='json_contests_path',
            help=("path to a contests.json file.  If provided, also adds the contest "
                  "to the end of the given JSON file."))


# TODO: allow passing a contest ID to clean up just one contest.
# TODO: accept a normalize option and default to not normalizing ballots.
class CleanContestsCommand(CommandBase):

    name = "cleancontests"
    help = "Clean and normalize a contests.json file."

    @property
    def func(self):
        return commands.clean_contests

    @property
    def desc(self):
        return dedent("""\
            Clean and normalize a contests.json file.

            For example, this command updates the integer contest IDs.
            """)

    def add_arguments(self, parser):
        parser.add_argument('json_contests_path', metavar='JSON_PATH',
            help=("path to a contests.json file."))


# TODO: unit-test print_help().
def create_argparser(prog="rcv"):
    """
    Return an ArgumentParser object.
    """
    parser = RcvArgumentParser(prog=prog, description=DESCRIPTION, add_help=False,
                               formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('--log-level', metavar='LEVEL',
        default=LOG_LEVEL_DEFAULT, type=parse_log_level,
        help=("logging level name or number (e.g. CRITICAL, ERROR, WARNING, "
              "INFO, DEBUG, 10, 20, etc). "
              "Defaults to %s." % LOG_LEVEL_DEFAULT_NAME))
    add_help(parser)

    desc = dedent("""\
    Available commands are below.

    For help with a particular command, pass %s after the command name.
    For example, `%s count %s`.
    """ % (OPTION_HELP.display(' or '), prog, OPTION_HELP[0]))
    subparsers = parser.add_subparsers(title='commands', metavar='COMMAND',
                                       description=desc)
    subparsers.formatter_class = RawDescriptionHelpFormatter

    command_classes = [
        CountCommand,
        RandContestCommand,
        CleanContestsCommand,
    ]

    builder = ArgParserBuilder(subparsers)
    for cls in command_classes:
        command = cls(builder)
        command.add()

    return parser


# TODO: move this to openrcv.formats.common.
class OutputFormat(object):

    def __init__(self, label, desc=None, cls=None):
        self.cls = cls
        self.desc = desc
        self.label = label

    def __str__(self):
        return '"{!s}" ({!s})'.format(self.label, self.desc)


class ArgParserBuilder(object):

    """Support for constructing the script's argparse.ArgumentParser."""

    def __init__(self, subparsers):
        self.formats = make_output_formats()
        self.subparsers = subparsers

    def writer_type(self, label):
        formats = self.formats
        try:
            format = formats[label]
        except KeyError:
            labels = sorted(formats.keys())
            raise argparse.ArgumentTypeError("\ninvalid argument choice: %r "
                "(choose from: %s)" % (label, ", ".join(labels)))
        return format.cls


class RcvArgumentParser(ArgParser):

    option_help = OPTION_HELP

    def safe_get_log_level(self, args, error_level=None):
        """
        Get the user-requested log level without raising an exception.

        Returns the log level as an integer.

        Arguments:
          error_level: the log level that should be used if a UsageException occurs.
        """
        if error_level is None:
            error_level = LOG_LEVEL_USAGE_ERROR
        try:
            ns = self.parse_args(args=args)  # Namespace object
        except UsageException:
            level = parse_log_level(error_level)
        else:
            level = ns.log_level
        return level
