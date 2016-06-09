from django.db import models
from django.contrib.auth.models import User
from datetime import datetime

# Create your models here.

def user_is_patient(user):
    return hasattr(user, 'patient')
def user_is_nurse(user):
    return hasattr(user, 'nurse')
def user_is_doctor(user):
    return hasattr(user, 'doctor')
def user_is_admin(user):
    return hasattr(user, 'administrator')

def user_type_string(user):
    if user_is_patient(user):
        return 'patient'
    elif user_is_nurse(user):
        return 'nurse'
    elif user_is_doctor(user):
        return 'doctor'
    elif user_is_admin(user):
        return 'admin'
    else:
        raise Exception("Broken user: isn't of any known type")

class Administrator(models.Model):
    parent = models.OneToOneField(User)

class Patient(models.Model):
    parent              = models.OneToOneField(User)
    phone               = models.CharField(max_length=16)
    insurance_company   = models.CharField(max_length=64)
    insurance_id        = models.CharField(max_length=64)
    hospital            = models.ForeignKey(
        'Hospital',
        on_delete=models.SET_NULL,
        null=True)
    pcp = models.ForeignKey('Doctor', on_delete=models.CASCADE, default=None, null=True)

    GENDER_MALE   = 1
    GENDER_FEMALE = 2
    GENDER_OTHER  = 3
    gender_choices = (
        (GENDER_MALE, 'Male'),
        (GENDER_FEMALE, 'Female'),
        (GENDER_OTHER, 'Other'),
    )

    gender              = models.IntegerField(choices=gender_choices, default=GENDER_OTHER)
    height              = models.IntegerField(default=0)
    weight              = models.IntegerField(default=0)

    EYE_BROWN = 1
    EYE_BLUE  = 2
    EYE_GREEN = 3
    EYE_HAZEL = 4
    EYE_OTHER = 5
    eye_color_choices = (
        (EYE_BROWN, 'Brown'),
        (EYE_BLUE,  'Blue' ),
        (EYE_GREEN, 'Green'),
        (EYE_HAZEL, 'Hazel'),
        (EYE_OTHER, 'Other'),
    )
    eye_color           = models.IntegerField(choices=eye_color_choices, default=EYE_BROWN)
    BLOOD_A  = 1
    BLOOD_a  = 2
    BLOOD_B  = 3
    BLOOD_b  = 4
    BLOOD_O  = 5
    BLOOD_o  = 6
    BLOOD_AB = 7
    BLOOD_ab = 8
    blood_type_choices = (
        (BLOOD_A,  'A+' ),
        (BLOOD_a,  'A-' ),
        (BLOOD_B,  'B+' ),
        (BLOOD_b,  'B-' ),
        (BLOOD_O,  'O+' ),
        (BLOOD_o,  'O-' ),
        (BLOOD_AB, 'AB+'),
        (BLOOD_ab, 'AB-'),
    )

    blood_type          = models.IntegerField(choices=blood_type_choices, default=BLOOD_AB)
    allergies           = models.TextField(default='')
    birth_date          = models.DateField(default=datetime.today())
    
class Hospital(models.Model):
    name     = models.CharField(max_length=128)
    location = models.CharField(max_length=256)

class Doctor(models.Model):
    parent = models.OneToOneField(User)
    hospitals = models.ManyToManyField(Hospital)
    
class Nurse(models.Model):
    parent = models.OneToOneField(User)
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.SET_NULL,
        null=True)

class Prescription(models.Model):
    drug      = models.CharField(max_length=128)
    amount    = models.CharField(max_length=16)
    startdate = models.DateField()
    enddate   = models.DateField()
    notes     = models.TextField()
    patient   = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE)
    doctor    = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE)

class Event(models.Model):
    name        = models.TextField()
    start       = models.DateTimeField()
    end         = models.DateTimeField()
    location    = models.CharField(max_length=128)
    description = models.TextField()
    attendees   = models.ManyToManyField(User)

class Test(models.Model):
    name     = models.CharField(max_length=256)
    results  = models.TextField()
    notes    = models.TextField()
    doctor   = models.ForeignKey(Doctor)
    patient  = models.ForeignKey(Patient)
    released = models.BooleanField()


class Visit(models.Model):
    admission = models.DateTimeField()
    discharge = models.DateTimeField()
    hospital  = models.ForeignKey(Hospital)
    reason    = models.TextField()
    patient   = models.ForeignKey(Patient)

class Record(models.Model):
    time    = models.DateTimeField()
    patient = models.ForeignKey(Patient)
    title   = models.TextField()
    body    = models.TextField()

class Logging(models.Model):
    time        = models.DateTimeField()
    title       = models.TextField()
    user        = models.ForeignKey(User,null=True)
    description = models.TextField()

class Medication(models.Model):
    name = models.TextField()

class Admission(models.Model):
    description = models.TextField()
    patient  = models.ForeignKey(Patient)
    hospital = models.ForeignKey(Hospital)

class Transfer(models.Model):
    patient = models.ForeignKey(Patient,
                                on_delete=models.CASCADE)
    hospital = models.ForeignKey(Hospital,
                                 on_delete=models.CASCADE)
    time = models.DateTimeField()

class Message(models.Model):
    src   = models.ForeignKey(
                User,
                on_delete=models.CASCADE,
                related_name="sent")
    dest  = models.ForeignKey(
                User,
                on_delete=models.CASCADE,
                related_name="inbox")
    time  = models.DateTimeField()
    title = models.TextField()
    body  = models.TextField()
