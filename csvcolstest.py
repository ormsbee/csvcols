import string
from unittest import TestCase

from nose.tools import *

from csvcols import Column, Document


class TestDocument(TestCase):

    def setUp(self):
        self.first_name = Column(["David", "Brian", "Sonya", "Alexis"])
        self.last_name = Column(["Smith", "Lee", "Kim", "Doe"])
        self.gender = Column(["Male", "Male", "Female", "Female"])

        self.users_doc = Document([("first_name", self.first_name),
                                   ("last_name", self.last_name),
                                   ("gender", self.gender)])

    def test_accessors(self):
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

    def test_mapping(self):
        caps_users = self.users_doc.map(string.upper)
        assert_equal(caps_users.first_name,
                     Column(["DAVID", "BRIAN", "SONYA", "ALEXIS"]))
        assert_equal(caps_users.last_name,
                     Column(["SMITH", "LEE", "KIM", "DOE"]))
        assert_equal(caps_users.gender,
                     Column(["MALE", "MALE", "FEMALE", "FEMALE"]))
        



# Implementation priority order
#  - select, select_if / reject, reject_if
#       select_if()
#  - sorted_columns, sorted_by("col1", "col2", "col3")
#  - merge_by
#
#Document(sorted(doc))
#
#
# 
# def test_cg():
#     cg = Document(first_name=["Dave", "Sonya", "Brian", "Alexis"],
#                   last_name=["Smith", "Jones", "Doe", "Doe"],
#                     ))
# 
#     assert_equal(len(cg.last_name), 4)
# 
