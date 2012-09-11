"""
TODO list:

* dumps
* Document.sort_rows
* Document.merge_rows_on
* Document.merge_rows_if
* Document append Document or ("col_nae", col) tuple
* deal with errors in transforms
"""
import csv
from collections import namedtuple, OrderedDict
from cStringIO import StringIO
from itertools import imap, izip

class Column(tuple):
    """An immutable sequence of elements that represent every element in a 
    column of the CSV file. It should provide for both iteration and random
    access (i.e. implement the Sequence ABC).

    While it is possible to create a column with any data types in it, when the
    Column comes from a Document's parsing methods, it always contains Unicode
    strings.
    
    The implementation is intentionally kept very simple here (leaning almost
    entirely on tuple). There are many fun possilibites for more memory 
    efficient structures. Many columns tend to have data that is extremely 
    bursty (many blanks followed by many of the same value) or have a very 
    small set of possible values ("M/F", "Y/N", etc.), lending themselves well 
    to bitarray or RLE encodings. But memory efficiency isn't a major goal for 
    this iteration, so we'll just do the simplest thing. Later on, we'd probably
    make Column an instance of an ABC.
    """
    def __eq__(self, other):
        """We're a little more forgiving than a tuple comparison -- we'll allow
        comparisons to lists and other iterables by casting them to tuples."""
        return super(Column, self).__eq__(tuple(other))

    @property
    def unique(self):
        """Return a frozenset of the unique elements in this Column."""
        return frozenset(self)

class Document(object):
    """A Document is a way to group Columns together and give them names.
    A Column object is just data, it has no name or identifier.  This is a
    helpful abstraction because many times the same column data is referenced
    under many different names in slightly modified versions of a Document.
    Columns are immutable, so Documents share them, and creating a new Document
    from existing Columns is cheap.

    Creating a Document automatically creates a Row object for that Document.
    The Row object is a subclass of `namedtuple` and is also accessible by 
    string index like a dictionary, for those cases in which column names don't
    cleanly map to a valid Python attribute name. For example::

        my_doc = Document([("first_name", first_name_col),
                           ("-LAST NAME-", last_name_col),
                           ("email", email_col)])
        for row in my_doc.iterrows():
            # Each row is an instance of the my_doc.Row class
            print row.first_name   # access like a named tuple
            print row["-LAST NAME-"] # access using column names
            print row[2] # access with simple index

    """
    def __init__(self, name_col_pairs):
        """`name_col_pairs` must be an iterable of (Unicode, Column) tuples, 
        where the strings are column names. Column names must be unique. Column
        lengths must be the same. It is valid to have an empty Document, where
        all columns have zero elements.

        A :exc:`TypeError` is raised if any of these requirements is not met.
        """
        # We force expansion in case it's a generator, and force our names to be
        # in unicode. This is intended for the case where it's invoked with 
        # hard-coded names in code. Parsing code should always call this method
        # with unicode names instead of relying on this method to do it.
        name_col_pairs = [(unicode(name), col) for name, col in name_col_pairs]
        self._names_to_cols = OrderedDict(name_col_pairs)
        if not self._names_to_cols:
            raise TypeError("Document must have at least one Column")
        if len(name_col_pairs) != len(self._names_to_cols):
            raise TypeError("Document must have unique names for Columns: %s" %
                            [name for name, col in name_col_pairs])

        # Check: All columns have the same length
        column_lengths = [len(col) for col in self.columns]
        if len(frozenset(column_lengths)) > 1:
            raise TypeError("Document's Columns must have the same length: " \
                            "%s" % zip(self.names, column_lengths))

        # We create a custom Row object for every Document, that you can use 
        # either as a tuple or an ordered dict. Accessible via rows or iterrows()
        self.Row = self._create_row_class()
        
        # Caching
        self._cached_rows = None

    def _create_row_class(self):
        Row = namedtuple('Row', self.names, rename=True)
        Row._names_to_indexes = OrderedDict((name, i) for i, name
                                            in enumerate(self.names))
        def _row_get_item_by_name(row_obj, name_or_index):
            if isinstance(name_or_index, basestring):
                index = row_obj._names_to_indexes[name_or_index]
            else:
                index = name_or_index
            return tuple.__getitem__(row_obj, index)

        Row.__getitem__ = _row_get_item_by_name

        return Row

    ############################# Simple Accessors #############################
    @property
    def columns(self):
        """An ordered list of the Column objects in this Document."""
        return self._names_to_cols.values()

    @property
    def names(self):
        """An ordered list of the column names in this Document."""
        return self._names_to_cols.keys()

    @property
    def rows(self):
        """Return the entire Document as a tuple of `self.Row` objects."""
        if self._cached_rows is None:
            self._cached_rows = tuple(self.iterrows())
        return self._cached_rows

    @property
    def num_rows(self):
        """All Columns in this Document are the same length, and a Document
        must have at least one Column, so we just return its length."""
        return len(self[0])

    def iterrows(self):
        """Iterate through the Document row by row. Returns a generator of 
        `self.Row` objects, which can be treated as a namedtuple or accessed
        by column name like a dictionary::

            for row in my_doc.iterrows():
                # Each row is an instance of the my_doc.Row class
                print row.first_name   # access like a named tuple
                print row["-LAST NAME-"] # access using column names
                print row[3] # access with simple index
        """
        return (self.Row(*row_vals) for row_vals in izip(*self.columns))

    ################# Creating new Documents based on this one #################
    def map(self, **names_to_funcs):
        """Return a Document where the column names in `names_to_funcs` have
        been transformed by applying the corresponding functions in
        `names_to_funcs`. The appropriate function will be applied to every
        element of the corresponding Column. Example::
        
            lower_cased_doc = user_doc.map(name=unicode.lower, email=unicode.lower)
        """
        def _mapped_col(name, col):
            if name in names_to_funcs:
                return Column(imap(names_to_funcs[name], col))
            return col
        
        return Document((name, _mapped_col(name, col)) for name, col in self)

    def map_all(self, f):
        """Return a new Document that has the same column names as this
        Document, but who's Columns have been transformed by applying `f` to
        each element of each Column. Example::

            lower_cased_doc = user_doc.map_all(unicode.lower)
        """
        return Document((name, Column(imap(f, col))) for name, col in self)

    def select(self, *selector_objs):
        """Create a new Document by selecting and optionally transforming 
        Columns from this one. `selector_objs` can be an iterable of 
        :class:`Selector`, but it can also have strings or tuples. A string
        will be interpreted as a :class:`Selector` with only the column name
        specified. Tuples will be sent as constructor arguments to 
        :class:`Selector`.

        So for example, all of these will work::

            users_doc = raw_shipping_doc.select(
                S("email", transform=unicode.lower),
                S("BILLING_LAST", rename="last_name", transform=unicode.title),
                S("BILLING_FIRST", rename="first_name"),
                ("CUSTOM 1", "special_notes"), # This will cause a rename
                "country" # This just selects this column
            )

        """
        # Make sure they're all Selector objects
        selectors = [Selector.from_unknown(obj) for obj in selector_objs]
        return Document(s(self) for s in selectors)

    def cols_sorted(self, cmp=None, key=None, reverse=False):
        """Return a Document that is the same as this one, except where the
        columns are sorted by name. It takes the same keyword args as the
        `sorted` built in, so you can customize how things are compared."""
        return self.select(*sorted(self.names, cmp, key, reverse))

#    def rows_sorted_by(self, *names, cmp=None, key=None, reverse=False):
#        if not names:
#            return Document.from_rows(self.names, sorted(self.rows))

    ############################## Constructors ################################
    @classmethod
    def from_rows(cls, names, rows):
        """Convenience method to create a Document by specifying a list of 
        column names (`names`) and an iterable of `rows` (where each row is also
        an iterable)."""
        # Force it to a list so that we can tell if it's empty (generators will
        # return true even if they're empty).
        rows = list(rows)
        if not rows: # no rows because it's None or an empty list (just a header)
            return cls((name, Column()) for name in names)
        else:
            cols = [Column(col) for col in zip(*rows)]
            return cls(zip(column_names, cols))

    ################################ Built-ins #################################
    def __add__(self, other):
        return Document(zip(self.names + other.names, 
                            self.columns + other.columns))

    def __contains__(self, name_or_col):
        return (name_or_col in self.names) or (name_or_col in self.columns)

    def __eq__(self, other):
        # Don't compare with self._names_to_cols directly (order matters).
        return (self.names == other.names) and (self.columns == other.columns)

    def __iter__(self):
        return self._names_to_cols.iteritems()

    def __getattr__(self, name):
        try:
            return self._names_to_cols[name]
        except KeyError:
            raise AttributeError(name)

    def __getitem__(self, index):
        """Get column either by ordered index, or by column name."""
        if isinstance(index, int):
            return self.columns[index]
        elif isinstance(index, basestring):
            return self._names_to_cols[index]
        else:
            raise TypeError("Document indices must be basestring or int, " \
                            "not %s" % type(index))

    def __len__(self):
        return len(self._names_to_cols)


class Selector(object):
    """A Selector object (aliased to `S` for convenience) describes a column
    that we want to extract and optionally rename or transform the contents of.
    """
    def __init__(self, select, rename=None, transform=None):
        """`select` is the name of the column we want to extract from a 
        Document.

        `rename` is the new name we're going to give it.

        `transform` is a function to apply to each element in the extracted 
        Column.

        Mostly, you'll just want to use this when you're building arguments for
        :func:`Document.select`, but you can also use it by itself like::

            email_selector = Selector("email")
            col_name, col = email_selector(user_doc)
        """
        self._select = select
        self._rename = rename
        self._transform = transform

    def __call__(self, doc):
        """Apply this Selector to a given Document. Returns a `(name, Column)`
        pair."""
        name = self._rename if self._rename is not None else self._select
        if self._transform:
            col = Column(self._transform(x) for x in doc[self._select])
        else:
            col = doc[self._select]
        return (name, col)

    @classmethod
    def from_unknown(cls, obj):
        if isinstance(obj, cls):
            return obj
        elif isinstance(obj, basestring):
            return cls(obj)
        elif isinstance(obj, tuple):
            return cls(*obj)
        else:
            raise TypeError("Can't create Selector from {0}".format(cls))

# Shorthand for export purposes. I know there's a better way to do this.
S = Selector

def load(csv_stream, strip_spaces=True, skip_blank_lines=True,
         encoding="utf-8", delimiter=",", force_unique_col_names=False):
    """Load CSV from a file or StringIO stream. If `strip_spaces` is True (it is
    by default), we will strip leading and trailing spaces from all entries. If
    skip_blank_lines is True, we ignore all lines for which there is no data in
    the row. Excel often does both of these when exporting to CSV, giving you 
    rows upon rows of output that looks like ",,,,,,,".
    
    The encoding is utf-8 by default. Another really common encoding for older
    systems is latin-1
    """
    def _force_unique(col_headers):
        seen_names = set()
        unique_col_headers = list()
        for i, col_name in enumerate(col_headers):
            if col_name in seen_names:
                col_name += "_%s" % i
            seen_names.add(col_name)
            unique_col_headers.append(col_name)
        return unique_col_headers

    def _pad_row(row):
        if len(row) < num_cols:
            for i in range(num_cols - len(row)):
                row.append('')
        return row

    def _process_row(row):
        if strip_spaces:
            return _pad_row([value.strip() for value in row])
        else:
            return _pad_row(row)

    csv_reader = csv.reader(csv_stream, delimiter=delimiter)

    column_headers = [header.strip() for header in csv_reader.next()]
    if force_unique_col_names:
        column_headers = _force_unique(column_headers)
    num_cols = len(column_headers)

    # Make a list to gather entries for each column in the data file...
    raw_text_cols = [list() for i in range(num_cols)]
    for row in csv_reader:
        processed_row = _process_row(row)
        # Add this new row if we either allow blank lines or if any field
        # in the line is not blank. We do this to the processed row,
        # because spaces may or may not be significant, depending on
        # whether strip_spaces is True.
        if (not skip_blank_lines) or any(processed_row):
            for i in range(num_cols):
                raw_text_cols[i].append(processed_row[i].decode(encoding))

    # Now take the raw data and put it into our Column...
    cols = [Column(raw_col) for raw_col in raw_text_cols]

    return Document(zip(column_headers, cols))

def loads(csv_str, *args, **kwargs):
    return load(StringIO(csv_str), *args, **kwargs)
    
def dump(doc, stream):
    pass

def dumps(doc):
    pass

