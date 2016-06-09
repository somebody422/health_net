from django.test import TestCase
from .validation import *

# Create your tests here.

class Test_validate_insurance(TestCase):
    def test_short(self):
        test_str = "A123"
        self.assertFalse(validate_insurance(test_str))

    def test_long(self):
        test_str = "A1234567890000000000"
        self.assertFalse(validate_insurance(test_str))

    def test_proper(self):
        test_str = "B123AZ9985F3"
        self.assertTrue(validate_insurance(test_str))

    def test_bad_char_type(self):
        test_str = "%%%%%%%%%%%%"
        self.assertFalse(validate_insurance(test_str))

class Test_validate_name(TestCase):
    def test_blank(self):
        test_str = ""
        self.assertFalse(validate_name(test_str))

    def test_full_name(self):
        test_str = "Liam Kane"
        self.assertFalse(validate_name(test_str))
        # False because of space

    def test_non_alpha(self):
        test_str = "#"
        self.assertFalse(validate_name(test_str))

    def test_proper(self):
        test_str = "Liam"
        self.assertTrue(validate_name(test_str))

class Test_validate_phone(TestCase):
    def test_short(self):
        test_str = "012"
        self.assertFalse(validate_phone(test_str))

    def test_long(self):
        test_str = "0123456789999999999"
        self.assertFalse(validate_phone(test_str))

    def test_good_len(self):
        test_str = "0123456789"
        self.assertTrue(validate_phone(test_str))

    def test_unfortunate_success(self):
        test_str = "AAAAA0123456789BBBBB"
        self.assertTrue(validate_phone(test_str))

class Test_validate_prescription_functions(TestCase):
    def test_dates_front_back(self):
        a = "2000-01-01"
        time_a = datetime.strptime(a, "%Y-%m-%d")
        self.assertFalse(validate_prescription_dates(datetime.today(), time_a))
        self.assertTrue(validate_prescription_dates(time_a, datetime.today()))

    def test_dates_equal(self):
        self.assertTrue(validate_prescription_dates(datetime.today(), datetime.today()))

    def test_start_future(self):
        a = "2020-01-01"
        self.assertTrue(validate_presciption_start(a))

    def test_start_now(self):
        b = datetime.strftime(datetime.today(), "%Y-%m-%d")
        print("\n\n", b, "\n")
        self.assertFalse(validate_presciption_start(b))

    def test_start_past(self):
        a = "2000-01-01"
        self.assertFalse(validate_presciption_start(a))

class Test_validate_dob(TestCase):
    def test_future(self):
        self.assertFalse(validate_dob("2050-01-01"))

    def test_past(self):
        self.assertTrue(validate_dob("2000-01-01"))

    def test_today(self):
        a = datetime.strftime(datetime.today(), "%Y-%m-%d")
        self.assertTrue(validate_dob(a))

class Test_validate_weight(TestCase):
    def test_too_light(self):
        self.assertFalse(validate_weight(-7))

    def test_too_heavy(self):
        self.assertFalse(validate_weight(1000))

    def test_proper_weight(self):
        self.assertTrue(validate_weight(200))

class Test_validate_height(TestCase):
    def test_too_short(self):
        self.assertFalse(validate_height(-1))

    def test_too_tall(self):
        self.assertFalse(validate_height(180))

    def test_good_height(self):
        self.assertTrue(validate_height(65))