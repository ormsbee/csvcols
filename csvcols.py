import csv
from collections import namedtuple, OrderedDict
from itertools import izip

class Column(tuple):
    """An immutable list of elements that represent every element in a column of
    the CSV file. It should provide for both iteration and random access (i.e.
    implement the Sequence ABC).

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
    def __init__(self, *args):
        super(Column, self).__init__(*args)
        self._unique = None # For caching unique set of values, not often called

    @property
    def unique(self):
        if self._unique == None:
            self._unique = frozenset(self)
        return self._unique


class Document(object):
    """A Document is a way to group Columns together and give them names.
    A Column object is just data, it has no name or identifier.  This is a
    helpful abstraction because many times the same column data is referenced
    under many different names in slightly modified versions of a Document.

    sorted_cols
    sorted_rows
    merged_rows
    map vs. map_all in Document
    remove map from Column?
    select
    select_by
    sort_by
    sort
    
    """

    def __init__(self, name_col_pairs):
        """Return a new Document given either an iterable of (Unicode, Column)
        tuples, where the strings are column names; or an OrderedDict. Column 
        names must be unique. Column lengths must be the same.

        We force expansion in case it's a generator, and force our names to be
        in unicode. This is intended for the case where it's invoked with 
        hard-coded names in code. Parsing code should always call this method
        with unicode names instead of relying on this this method to do it.
        """
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
        return self._names_to_cols.values()

    @property
    def names(self):
        return self._names_to_cols.keys()

    @property
    def rows(self):
        if self._cached_rows == None:
            self._cached_rows = tuple(self.iterrows())
        return self._cached_rows

    def iterrows(self):
        return (self.Row(*row_vals) for row_vals in izip(*self.columns))

    def map(self, **names_to_funcs):
        """Take keyword arguments
        
        user_info.map(name=unicode.title, email=unicode.lower)        
        """
        def _mapped_col(name, col):
            if name in names_to_funcs:
                return Column(map(names_to_funcs[name], col))
            return col
        
        return Document((name, _mapped_col(name, col)) for name, col in self)

    def map_all(self, f):
        return Document((name, Column(map(f, col))) for name, col in self)

    ############################## Constructors ################################
    @classmethod
    def from_rows(cls, names, rows):
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


def loads(csv_str, *args, **kwargs):
    return load(StringIO(csv_input), *args, **kwargs)

def load(csv_input, strip_spaces=True, skip_blank_lines=True,
         encoding="utf-8", delimiter=",", force_unique_col_names=False):
    """Load CSV from a file or StringIO stream. If strip_spaces is True (it is
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
    
