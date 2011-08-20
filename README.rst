csvcols: an immutable, column-oriented CSV manipulation library
===============================================================

This library takes a column-oriented approach towards CSV data. Everything is
stored internally as Unicode, and everything is outwardly immutable. It has 
support for:

* Parsing CSV files, including some Excel exported quirks
* Selecting and renaming columns
* Merging rows
* Re-sorting a document by columns or rows
* Creating new documents by appending old ones together
* Transforming (map, map_all) documents by column

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
    shipping_doc = csvcols.load("shipping_orders.csv")

    # Extract just the columns we care about, and rename some of them
    raw_users_doc = shipping_doc.select("email", 
                                        ("BILLING_FIRST", "first_name"),
                                        ("BILLING_LAST", "last_name"))

    # Title case the name columns, lowercase the email column. If you're using
    # string functions, be careful that you use the unicode.xxx ones, and not
    # str.xxx
    users_doc = raw_users_doc.map(first_name=unicode.title,
                                  last_name=unicode.title,
                                  email=unicode.lower)

    # Sort rows by email, then last name, then first name
    sorted_doc = users_doc.sort_rows("email", "last_name", "first_name")

    def _merge_if(row1, row2):
        return row1.email == row2.email and \
               row1.last_name == row2.last_name and \
               row1.first_name[0] == row2.first_name[0]

    def _merge_how(row1, row2):
        return row1 if len(row1.first_name) > len(row2.first_name) else row2

    # Merge duplicate rows, as defined by the above helper functions
    merged_doc = sorted_doc.merge_rows(_merge_if, _merge_how)
    
    # Create a new column based on an existing one...
    is_edu_user_col = Column("Y" if s.endswith(".edu") else "N"
                             for s in merged_doc.email)

    # Append this new column to the doc (note: this creates a new doc)
    final_doc = merged_doc + is_edu_user_col

    print cvscols.dumps(final_doc)
    print "Unique emails: %s" % sorted(final_doc.email.unique)

    # Make a new document based on raw_users, where the email column is 
    # replaced by a copy that's been transformed into lowercase.
    sorted_users = users.sort_rows_by("email", "last_name", "first_name")
    merged_users = sorted_users.merge_if(lambda r1, r2: "email")

Recommendations
---------------
For non-trivial work, try to break up your manipulations into stages, with each
stage represented as a Document. It makes it much easier to isolate where things
went wrong and why. Also, you can use select() to break documents into logical pieces. For instance, an orders invoice file might be broken up into "users",
"contact_info", "items". It's much easier to follow if you have methods that 
take a sub-document or just a few columns and operate on those, rather than 
having every method take a massive document and spit one back. You can later 
reconstruct the document by appending your pieces together. Just remember to 
rebuild the document with all the columns you care about before sorting.

Also, while csvcols will parse files into Columns of unicode data, it doesn't 
mean that you have to use unicode strings for all your Columns. If making an 
intermediate column datetime makes your life easier, by all means do it. The 
same goes for having a real None value rather than overloading blanks to 
sometimes be an empty string and sometimes be a logical null. Remember that you
can serialize Columns and Documents as JSON, so you can store more complicated data structures.

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
fast (there's some very simple caching for row values and to get unique vals).
I didn't need it at this point, but it should be pretty feasible, since Column
data tends to be highly redundant in real life.