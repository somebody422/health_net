# **************************************
# This file contains validation functions for use in various Views.
# Any data validation should be done by functions in this file.
# **************************************

from django.contrib.auth.models import User
from .models import *

# Name:         check_post_fields
# Description:  check that post contains all fields
# Arguments:     post a request.POST
#               fields a dict of fields to be in post
# Returns:      An error string for the first missing field
#               None if no field is missing
def check_post_fields(post, fields):
    for field in fields:
        if (field not in post) or post[field] == '':
            return "The %s field is required" % field
    return None

# Name:         validate_insurance
# Description:  Check that id_num is exactly 12 characters, starting with an
#               alphabetic character, and containing only alphanumeric
#               characters.
# Arguments:    id_num, a potential insurance number
# Returns:      True if id_num is a valid insurance ID number; False otherwise.
def validate_insurance(id_num):
    if len(id_num) != 12:
        return False
    if not id_num[0].isalpha():
        return False
    else:
        for char in id_num:
            if not char.isalnum():
                return False
    return True

# Name:         unique_insurance
# Description:  Check that an insurance number is not already in use
# Arguments:    id_num, a potential insurance number
# Returns:      True if id_num has NOT been registered already; False otherwise
def unique_insurance(id_num):
    p = Patient.objects.filter(insurance_id__exact=id_num)
    return not p.exists()

# Name:         validate_name
# Description:  Check that the string is only alphabetic characters
# Arguments:    name_string is a potential name
# Returns:      True if name_string exists and is not empty and contains only aphabetic characters
#               False otherwise
def validate_name(name_string):
    if name_string is None or name_string is '':
        return False
    for char in name_string:
        if not char.isalpha():
            return False
    return True

# Name:         validate_phone
# Description:  Ignore any non-digit character, check if there are 10 digits
# Arguments:    num is a potential phone number
# Returns:      True if num contains exactly ten digits, ignoring other chars
#               False otherwise
def validate_phone(num):
    if num is None or num is '':
        return False
    result_string = ''
    for char in num:
        if char.isdigit():
            result_string = result_string + char
    if len(result_string) == 10:
        return True
    return False

# Name:         unique_username
# Description:  Check if the provided name already is owned by another user
# Arguments:    name the username to check against
# Returns:      True if this name is acceptable
#               False otherwise
def unique_username(name):
    u = User.objects.filter(username__exact=name)
    return not u.exists()

# Name:         validate_prescription_dates
# Description:  Check if the prescription start date is before the prescription end date
# Arguments:    start and end date of the prescription
# Returns:      True if the start date is before the end date
#               False otherwise
def validate_prescription_dates(start, end):
    return (start < end)

# Name:         validate_prescription_dates
# Description:  Check if the prescription start date is on or after today's date
# Arguments:    start date of the prescription
# Returns:      True if the start date is on or after today's date
#               False otherwise

def validate_presciption_start(start):
    return datetime.strptime(start, "%Y-%m-%d") > datetime.today()

# Name:         validate_dob
# Description:  Check that a provided date is not in the future
# Arguments:    date the date object to be checked
# Returns:      True if date is in the past, False if date is in the future
def validate_dob(date):
    try:
        dob = datetime.strptime(date, "%Y-%m-%d")
        d = datetime.today()
        if dob <= d:
            return True
        else:
            return False
    except:
        return False

# Name:         validate_weight
# Description:  check that a provided weight is not less than 0 or greater than 600
# Arguments:    weight the weight to be checked
# Returns:      True if meets reqs, False otherwise
def validate_weight(weight):
    w = (int)(weight)
    if w < 0:
        return False
    if w > 600:
        return False
    return True

# Name:         validate_height
# Description:  check that a height is not less than 0 or greater than 9 ft
# Arguments:    height the height to be checked
# Returns:      True if desc parameters are met, false otherwise
def validate_height(height):
    h = (int)(height)
    if h < 0:
        return False
    if h > 108:
        return False
    return True