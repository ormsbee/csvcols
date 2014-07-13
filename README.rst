csvcols
=======

NOTE: Not recommended for use just yet, though I'm finally cleaning it up and
getting it that way as part of Julython.

This library takes a column-oriented approach towards CSV data. Everything is
stored internally as Unicode, and everything is outwardly immutable. It has
support for:

* Parsing CSV files, including some Excel exported quirks
* Selecting and renaming columns
* Transforming documents by column
* Re-sorting a document by columns or rows
* Creating new documents by appending old ones together
* Merging rows

CSV files are everywhere and every language has a library to read them row by
row. But sometimes that's not the best way to look at it. You often want to
make manipulations, transform or make rule checks on certain columns. If you
keep the row by row model, then you just end up trying to jam everything into a
single pass over the data. Or maybe you suck up everything into a 2D data
structure and edit it in several passes. But then you start having side-effects,
and you're not sure what changed what. Then you want to add a new rule that
requires data from an older pass through the data, and you start making
temporary data structures to hold the values of special columns or rows. I've
had the 800 lb gorilla version of this thrown on my lap. It's a maintenance
nightmare, and my frustrations with the code base inspired the creation of this
library.

The library in a nutshell::

    import csvcols
    from csvcols import Column, S # S = shorthand for Selector

    # Read Document from file. If encoding is not specified, UTF-8 is assumed.
    raw_shipping_doc = csvcols.load("shipping_orders.csv", encoding='latin-1')

    # Select a subset of the columns and make them into a new Document. While
    # we're doing this, we can rename or transform Columns.
    users_doc = raw_shipping_doc.select(
        S("email", transform=unicode.lower),
        S("BILLING_LAST", rename="last_name", transform=unicode.title),
        S("BILLING_FIRST", rename="first_name"),
        ("CUSTOM 1", "special_notes"), # We can use tuples for renames as well
        "country" # Or simple strings if we don't want to do any transforms
    )

    # If the email, last name, and first initial match, merge the records
    # together, and keep the longer first name. By default, this sorts as well.
    merged_doc = users_doc.merge_rows_on(
        lambda row: (row.email, row.last_name, row.first_name[0]),
        lambda r1, r2: r1 if len(r1.first_name) > len(r2.first_name) else r2
    )

    # Create a new Column based on existing data.
    is_edu_user_col = Column("Y" if s.endswith(".edu") else "N"
                             for s in merged_doc.email)

    # Append this new column to the doc (note: this creates a new doc)
    final_doc = merged_doc + ("is_edu_user", is_edu_user_col)

    print cvscols.dumps(final_doc)

Recommendations
---------------
For non-trivial work, try to break up your manipulations into stages, with each
stage represented as a Document. It makes it much easier to isolate where things
went wrong and why. Also, you can use select() to break documents into logical
pieces. For instance, an orders invoice file might be broken up into "users",
"contact_info", "items". It's much easier to follow if you have methods that
take a sub-document or just a few columns and operate on those, rather than
having every method take a massive document and spit one back. You can later
reconstruct the document by appending your pieces together. Just remember to
rebuild the document with all the columns you care about before sorting or
merging.

Also, while csvcols will parse files into Columns of unicode data, it doesn't
mean that you have to use unicode strings for all your Columns. If making an
intermediate column datetime makes your life easier, by all means do it. The
same goes for having a real None value rather than overloading blanks to
sometimes be an empty string and sometimes be a logical null. Remember that you
can serialize Columns and Documents as JSON, so you can store more complicated
data structures.

It's often the case that you have to flatten things out at the end to present it
back as a CSV to the user or to a legacy system. But while that data is in
transit between Excel and some legacy horror, you have a richer vocabulary and
should use it. For instance, an error column might hold dictionaries that
specify severity, type, etc. Just please, please, for the sake of your sanity,
don't start mutating the rich data structures inside the Column if you go this
route. There's nothing I can do to stop you, but down that path lies madness.

Warnings
--------
No attempt has been made to make this library memory efficient or particularly
fast. I didn't need it at this point, but it should be pretty feasible, since
Column data tends to be highly redundant in real life. I wrote a previous
incarnation of this library that actually had a lot of transform hashing and
caching (the idea was to prevent full recalcuation of a series of transforms
when only small parts of the document change), but it added more complexity
than it was worth, given how seldom I had a need for it.

Reference
---------
.. automodule:: csvcols
   :members:


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

