import string
from unittest import TestCase

from nose.tools import *

from csvcols import Column, Document, loads


class TestDocument(TestCase):

    def setUp(self):
        self.first_name = Column([u"David", u"Brian", u"Sonya", u"Alexis"])
        self.last_name = Column([u"Smith", u"Lee", u"Kim", u"Doe"])
        self.gender = Column([u"Male", u"Male", u"Female", u"Female"])

        self.users_doc = Document([("first_name", self.first_name),
                                   ("last_name", self.last_name),
                                   ("gender", self.gender)])

    def test_col_accessors(self):
        """Test basic ordered access to names and columns."""
        doc = self.users_doc

        assert_equal(doc.names, ["first_name", "last_name", "gender"])
        assert_equal(doc.columns,
                     [self.first_name, self.last_name, self.gender])

        assert_equal(doc.first_name, doc[0])
        assert_equal(doc.first_name, doc["first_name"])
        assert_equal(doc.last_name, doc[1])
        assert_equal(doc.last_name, doc["last_name"])
        assert_equal(doc.gender, doc[2])
        assert_equal(doc.gender, doc["gender"])

        assert_equal(len(doc.last_name), 4)

    
    def test_row_accessors(self):
        names_doc = Document([("First Name", self.first_name),
                              ("last_name", self.last_name),
                              ("class", Column(['1A', '1B', '1C', '1D']))])
        first_row = names_doc.rows[0]
        assert_equal(first_row["First Name"], "David")
        assert_equal(first_row["First Name"], first_row[0])
        assert_equal(first_row["last_name"], "Smith")
        assert_equal(first_row["last_name"], first_row.last_name)
        assert_equal(first_row["last_name"], first_row[1])
        assert_equal(first_row.last_name, "Smith")
        assert_equal(first_row["class"], "1A")
        assert_equal(first_row["class"], first_row[2])

    
    @raises(TypeError)
    def test_illegal_index(self):
        self.users_doc[1.27]

    def test_builtin_accessors(self):
        doc = self.users_doc

        assert_true("first_name" in doc)
        assert_true(self.last_name in doc)
        assert_false("first" in doc)
        assert_false(Column(["hi"]) in doc)

        # Even if it's not the exact same object, if the Columns are equal, 
        # this should return True
        assert_true(Column(["David", "Brian", "Sonya", "Alexis"]) in doc)
    
    def test_add_documents(self):
        doc1 = self.users_doc
        doc2 = Document([("last2", self.last_name),
                         ("first2", self.first_name)])
        combined_doc = doc1 + doc2
        
        assert_equal(len(combined_doc), len(doc1) + len(doc2))
        assert_equal(combined_doc.columns, doc1.columns + doc2.columns)
        assert_equal(combined_doc.names, doc1.names + doc2.names)

    @raises(TypeError)
    def test_duplicate_col_name(self):
        """Don't allow duplicate column names"""
        Document([("name", self.first_name), ("name", self.last_name)])

    @raises(TypeError)
    def test_uneven_columns(self):
        """Don't allow a Document where column lengths do not match."""
        dates = Column(["2011-05-22"])
        Document([("name", self.first_name), ("date", dates)])
    
    def test_row_iteration(self):
        doc = self.users_doc
        assert_equal(doc.rows[0].first_name, "David")

    def test_map_all(self):
        caps_users = self.users_doc.map_all(string.upper)
        assert_equal(caps_users.first_name,
                     Column(["DAVID", "BRIAN", "SONYA", "ALEXIS"]))
        assert_equal(caps_users.last_name,
                     Column(["SMITH", "LEE", "KIM", "DOE"]))
        assert_equal(caps_users.gender,
                     Column(["MALE", "MALE", "FEMALE", "FEMALE"]))

    def test_map(self):
        mapped_doc = self.users_doc.map(
                         first_name=unicode.upper,
                         last_name=unicode.lower,
                         gender=lambda g: g[0].upper(),
                     )
        assert_equal(mapped_doc.first_name,
                     ["DAVID", "BRIAN", "SONYA", "ALEXIS"])
        assert_equal(mapped_doc.last_name,
                     ["smith", "lee", "kim", "doe"])
        assert_equal(mapped_doc.gender,
                     ["M", "M", "F", "F"])

    def test_select(self):
        names = self.users_doc.select("last_name", "first_name")
        # Should be reordering
        assert_equal(names[0], self.users_doc.last_name)
        assert_equal(names[1], self.users_doc.first_name)

        multiple_copies = self.users_doc.select(
                              ("last_name", "last_1"),
                              ("last_name", "last_2"),
                              "last_name",
                              ("first_name", "first")
                          )
        assert_equal(multiple_copies.last_1, self.users_doc.last_name)
        assert_equal(multiple_copies.last_2, self.users_doc.last_name)
        assert_equal(multiple_copies.last_name, self.users_doc.last_name)
        assert_equal(multiple_copies.first, self.users_doc.first_name)


INVOICE_CSV_TEXT = """email,BILLING_FIRST,BILLING_LAST
dave@example.com,  Dave, ormsbee
,,,
rusty@example.com,Rusty,ormsbee
jack@example.com,Jack,  ,
clyde@example.com, clyde ,ormsbee,,,,,,,
,,,
"""

class TestLoading(TestCase):

    def test_skip_blank_lines(self):
        no_blanks = loads(INVOICE_CSV_TEXT, skip_blank_lines=True)
        assert_equal(no_blanks.num_rows, 4)

        with_blanks = loads(INVOICE_CSV_TEXT, skip_blank_lines=False)
        assert_equal(with_blanks.num_rows, 6)

    def test_strip_spaces(self):
        stripped = loads(INVOICE_CSV_TEXT, strip_spaces=True)
        assert_equal(stripped.BILLING_FIRST,
                     ["Dave", "Rusty", "Jack", "clyde"])
        assert_equal(stripped.BILLING_LAST,
                     ["ormsbee", "ormsbee", "", "ormsbee"])

        not_stripped = loads(INVOICE_CSV_TEXT, strip_spaces=False)
        assert_equal(not_stripped.BILLING_FIRST,
                     ["  Dave", "Rusty", "Jack", " clyde "])

















