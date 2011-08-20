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

    def test_mapping(self):
        caps_users = self.users_doc.map_all(string.upper)
        assert_equal(caps_users.first_name,
                     Column(["DAVID", "BRIAN", "SONYA", "ALEXIS"]))
        assert_equal(caps_users.last_name,
                     Column(["SMITH", "LEE", "KIM", "DOE"]))
        assert_equal(caps_users.gender,
                     Column(["MALE", "MALE", "FEMALE", "FEMALE"]))
        
x = """
import csvcols
shipping_doc = csvcols.load("shipping_orders.csv")

# Extract just the columns we care about, and rename some of them
raw_users_doc = shipping_doc.select("email", 
                                    ("BILLING_FIRST", "first_name"),
                                    ("BILLING_LAST", "last_name"))
# Transform the column data as necessary
users_doc = raw_users_doc.map(
                first_name=unicode.title,
                last_name=unicode.title,
                email=unicode.lower
            )
sorted_doc = users_doc.sort_rows("email", "last_name", "first_name")

def _merge_if(row1, row2):
    return row1.email == row2.email and \
           row1.last_name == row2.last_name and \
           row1.first_name[0] == row2.first_name[0]

def _merge_how(row1, row2):
    return row1 if len(row1.first_name) > len(row2.first_name) else row2

merged_doc = sorted_doc.merge_rows(_merge_if, _merge_how)
is_edu_user_col = merged_doc.email.map(
                      lambda s: "Y" if s.endswith(".edu") else "N"
                  )
is_edu_user_col = Column("Y" if s.endswith(".edu") else "N"
                         for s in merged_doc.email)

final_doc = merged_doc + is_edu_user_col

print cvscols.dumps(final_doc)
print "Unique emails: %s" % sorted(final_doc.email.unique)

# Make a new document based on raw_users, where the email column is 
# replaced by a copy that's been transformed into lowercase.
sorted_users = users.sort_rows_by("email", "last_name", "first_name")
merged_users = sorted_users.merge_if(lambda r1, r2: "email")


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
"""
