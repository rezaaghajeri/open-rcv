
from contextlib import contextmanager
import os
import tempfile
from tempfile import TemporaryDirectory

from openrcv import streams
from openrcv.streams import (tracked, ListResource, FilePathResource,
                             ReadWriteFileResource, StringResource)
from openrcv.utiltest.helpers import UnitCase


class FooException(Exception):
    pass


class TrackedTest(UnitCase):

    """Tests of tracked()."""

    def test(self):
        stream = ['a', 'b', 'c']
        gen = tracked("foo", stream)
        items = list(gen)
        self.assertEqual(items, ['a', 'b', 'c'])
        # Check that the return value exhausts (i.e. is an iterator object).
        items = list(gen)
        self.assertEqual(items, [])

    def test__exception(self):
        stream = ['a', 'b', 'c']
        gen = tracked("foo", stream)
        first = next(gen)
        self.assertEqual(first, "a")
        second = next(gen)
        with self.assertRaises(ValueError) as cm:
            gen.throw(ValueError("foo"))
        # Check the exception text.
        err = cm.exception
        self.assertEqual(str(err), "last read item from 'foo' (number=2): 'b'")
        # TODO: check that "foo" is also in the exception.

class StreamResourceTestMixin(object):

    """Base mixin for StreamResource tests."""

    def test_reading(self):
        with self.resource() as resource:
            with resource.reading() as stream:
                items = tuple(stream)
            self.assertEqual(items, ("a\n", "b\n"))
            # Check that you can read again.
            with resource.reading() as stream2:
                items = tuple(stream2)
            self.assertEqual(items, ("a\n", "b\n"))
            # Sanity-check that reading() doesn't return the same object each time.
            self.assertIsNot(stream, stream2)

    def test_reading__iterator(self):
        """Check that reading() returns an iterator [1].

        [1]: https://docs.python.org/3/glossary.html#term-iterator
        """
        with self.resource() as resource:
            with resource.reading() as stream:
                # Check that __iter__() returns itself.
                self.assertIs(iter(stream), stream)
                # Check that the iterable exhausts after iteration.
                items = tuple(stream)
                with self.assertRaises(StopIteration):
                    next(stream)
            self.assertEqual(items, ("a\n", "b\n"))

    def test_reading__error(self):
        """Check that an error while reading shows the line number."""
        with self.assertRaises(FooException) as cm:
            with self.resource() as resource:
                with resource.reading() as stream:
                    item = next(stream)
                    self.assertEqual(item, "a\n")
                    raise FooException()
        # Check the exception text.
        err = cm.exception
        self.assertStartsWith(str(err), "last read item from <%s:" % self.class_name)
        self.assertEndsWith(str(err), "(number=1): 'a\\n'")

    def test_writing(self):
        with self.resource() as resource:
            with resource.writing() as stream:
                stream.write('c\n')
                stream.write('d\n')
            with resource.reading() as stream:
                items = tuple(stream)
            self.assertEqual(items, ('c\n', 'd\n'))

    def test_writing__deletes(self):
        """Check that writing() deletes the current data."""
        with self.resource() as resource:
            with resource.reading() as stream:
                items = tuple(stream)
            self.assertEqual(items, ("a\n", "b\n"))
            with resource.writing() as stream:
                pass
            with resource.reading() as stream:
                items = tuple(stream)
            self.assertEqual(items, ())


class ListCoresourceTest(StreamResourceTestMixin, UnitCase):

    """ListResource tests."""

    class_name = "ListCoresource"

    @contextmanager
    def resource(self):
        yield streams.ListCoresource(["a\n", "b\n"])

    def test_writing(self):
        with self.resource() as resource:
            with resource.writing() as target:
                target.send('c\n')
                target.send('d\n')
            with resource.reading() as stream:
                items = tuple(stream)
            self.assertEqual(items, ('c\n', 'd\n'))

    def test_writing__deletes(self):
        """Check that writing() deletes the current data."""
        with self.resource() as resource:
            with resource.reading() as stream:
                items = tuple(stream)
            self.assertEqual(items, ("a\n", "b\n"))
            with resource.writing() as stream:
                pass
            with resource.reading() as stream:
                items = tuple(stream)
            self.assertEqual(items, ())

    def test_writing__error(self):
        """Check that an error while writing shows the line number."""
        return
        with self.assertRaises(ValueError) as cm:
            with self.resource() as resource:
                with resource.writing() as stream:
                    stream.send('c\n')
                    stream.send('d\n')
                    raise ValueError('foo')
        # Check the exception text.
        err = cm.exception
        self.assertStartsWith(str(err), "last written %s of <%s:" %
                              (self.expected_label, self.class_name))
        self.assertEndsWith(str(err), ": number=2, 'd\\n'")


class ListResourceTest(StreamResourceTestMixin, UnitCase):

    """ListResource tests."""

    class_name = "ListResource"

    @contextmanager
    def resource(self):
        yield ListResource(["a\n", "b\n"])


class FilePathResourceTest(StreamResourceTestMixin, UnitCase):

    """FilePathResource tests."""

    class_name = "FilePathResource"

    @contextmanager
    def resource(self):
        with TemporaryDirectory() as dirname:
            path = os.path.join(dirname, 'temp.txt')
            with open(path, 'w') as f:
                f.write('a\nb\n')
            yield FilePathResource(path)


class ReadWriteFileResourceTest(StreamResourceTestMixin, UnitCase):

    """ReadWriteFileResource tests."""

    class_name = "ReadWriteFileResource"

    @contextmanager
    def resource(self):
        with tempfile.TemporaryFile(mode='w+t', encoding='ascii') as f:
            f.write('a\nb\n')
            yield ReadWriteFileResource(f)


class SpooledReadWriteFileResourceTest(StreamResourceTestMixin, UnitCase):

    """ReadWriteFileResource tests (using tempfile.SpooledTemporaryFile)."""

    class_name = "ReadWriteFileResource"

    @contextmanager
    def resource(self):
        with tempfile.SpooledTemporaryFile(mode='w+t', encoding='ascii') as f:
            f.write('a\nb\n')
            yield ReadWriteFileResource(f)


# TODO: add StandardResource tests.

class StringResourceTest(StreamResourceTestMixin, UnitCase):

    """StringResource tests."""

    class_name = "StringResource"

    @contextmanager
    def resource(self):
        yield StringResource('a\nb\n')
