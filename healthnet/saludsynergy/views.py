from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.core.urlresolvers import reverse
from django.views import generic
from django.contrib import auth
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db import transaction
from datetime import datetime, timedelta
from django.core.exceptions import PermissionDenied
from .validation import *
from .models import user_is_patient
from .export import *
from django.utils import timezone
import itertools

from .models import *

def log_msg(user, title, description):
    log = Logging()
    log.time = datetime.now()
    log.title = title
    if user.is_anonymous():
        log.user = None
    else:
        log.user = user
    log.description = description
    log.save()

# ******************************************************************************
# Miscellaneous Views
# ******************************************************************************

# This generates a default context that is to be used whenever rendering a page
def defaultContext(request, sectionTitle):
    context = {
        'site_title': 'HealthNet',
        'section_title': sectionTitle,
        'display_navbar': False,
        'navbar_sections': [],
    }
    if request.user.is_authenticated():
        context.update({
                'display_navbar': True,
                'navbar_sections': [
                    {'name': 'Profile', 'url': reverse('profile_redirect')},
                    {'name': 'Calendar', 'url': reverse('calendar')},
                    {'name': 'Prescriptions', 'url': reverse('view_prescriptions', args=(request.user.pk,))},
                    {'name': 'Medical Records', 'url': reverse('view_medrec')},
                ],
                'user': request.user,
                'user_type': user_type_string(request.user),
            })
        if context['user_type'] == 'admin':
            context['navbar_sections'] += \
                [{'name': 'Activity Log', 'url': reverse('logging')} ,
                 {'name': 'System Statistics', 'url': reverse('systemstatistics')},
                 {'name': 'Export', 'url': reverse('jexport')}]
        if context['user_type'] == 'patient':
            context['navbar_sections'] += \
                [{'name': 'Transfer Hospitals', 'url': reverse('transfer_request')}]
        if context['user_type'] in ['admin', 'doctor', 'nurse']:
            context['navbar_sections'] += [{'name': 'Inbox', 'url': reverse('inbox')}]
    return context

def markActive(page, context):
    for item in context['navbar_sections']:
        if item['name'] == page:
            item['active'] = True

def assert_404(b):
    if not b:
        raise Http404("This is not the page you're looking for")

def login(request):
    if Administrator.objects.all().count() == 0:
        return redirect(reverse('register_admin_begin'))
    context = defaultContext(request, "Login")
    context['display_navbar'] = False
    if not request.POST:
        return render(request, 'login.html', context=context)
    else:
        err = check_post_fields(request.POST, ['email', 'password'])
        if err is not None:
            context['login_error'] = err
            return render(request, 'login.html', context=context)
        user = auth.authenticate(username=request.POST['email'], \
                                 password=request.POST['password'])
        if user is not None:
            if user.is_active:
                auth.login(request, user)
                if 'next' in request.POST:
                    return redirect(request.POST['next'])
                else:
                    return redirect(reverse('dashboard'))
            else:
                context['login_error'] = 'Sorry, your account has been disabled.'
                return render(request, 'login.html', context=context)
        else:
            context['login_error'] = 'Invalid email or password. Please try again.'
            return render(request, 'login.html', context=context)

def logout(request):
    auth.logout(request)
    return redirect(reverse('index'))

def index(request):
    if request.user.is_authenticated():
        return redirect(reverse('dashboard'))
    elif Administrator.objects.all().count() == 0:
        return redirect(reverse('register_admin_begin'))
    context = defaultContext(request, "Index")
    return render(request, 'index.html', context=context)

@login_required
def dashboard(request):
    context = defaultContext(request, 'Dashboard')
    context['user_type'] = user_type_string(request.user)
    if request.user.last_login is not None:
        context['last_login'] = request.user.last_login
    
    next_events = \
        Event.objects.filter(attendees__pk=request.user.pk).\
            filter(start__gt=datetime.now()).extra(order_by=['start'])
    
    context['num_events'] = len(next_events)
    if context['num_events'] > 0:
        context['next-event'] = next_events[0]
    
    if user_is_patient(request.user):
        context['prescriptions'] = Prescription.objects.filter(patient__parent__pk = request.user.pk)
        context['has_prescriptions'] = len(context['prescriptions']) > 0
        return render(request, 'dashboard_patient.html', context=context)
        
    elif user_is_doctor(request.user):
        context['admissions'] = Admission.objects.filter(patient__pcp__parent__pk = request.user.pk)
        if not context['admissions']:
            context['admission_error'] = 'None of your patients have been admitted'
        context['my_patients'] = Patient.objects.filter(pcp__parent__pk = request.user.pk)
        if not context['my_patients']:
            context['medrec_error'] = 'You have no patients'
        return render(request, 'dashboard_doctor.html', context=context)
    
    return render(request, 'dashboard.html', context=context)

# ******************************************************************************
# Register Views
# ******************************************************************************

# assume request.POST data is preserved if context not rebuilt
def register_step_1(request):
    context = defaultContext(request, "Register")
    return render(request, 'register_patient_1.html', context)

def register_step_2(request):
    context = defaultContext(request, "Register")
    if not request.POST:
        return redirect(reverse('index'))
    if 'cancel' in request.POST:
        return redirect(reverse('index'))
    #
    # Save data for redisplay
    #
    first_name = request.POST['first_name']
    last_name = request.POST['last_name']
    password = request.POST['password']
    email = request.POST['email']
    insurance = request.POST['insurance_id']
    company = request.POST['insurance_company']

    if 'first_name' not in request.POST or request.POST['first_name'] is '':
        context['last_name'] = last_name
        context['email'] = email
        context['insurance_company'] = company
        context['insurance_id'] = insurance
        context['register_error'] = "Your First Name cannot be blank."
        return render(request, 'register_patient_1.html', context)
    else:
        if not validate_name(first_name):
            context['last_name'] = last_name
            context['email'] = email
            context['insurance_company'] = company
            context['insurance_id'] = insurance
            context['register_error'] = "Your First Name can only contain letters."
            return render(request, 'register_patient_1.html', context)

    if 'last_name' not in request.POST or request.POST['last_name'] is '':
        context['first_name'] = first_name
        context['email'] = email
        context['insurance_company'] = company
        context['insurance_id'] = insurance
        context['register_error'] = "Your Last Name cannot be blank."
        return render(request, 'register_patient_1.html', context)
    else:
        if not validate_name(last_name):
            context['first_name'] = first_name
            context['email'] = email
            context['insurance_company'] = company
            context['insurance_id'] = insurance
            context['register_error'] = "Your Last Name can only contain letters."
            return render(request, 'register_patient_1.html', context)

    if 'email' not in request.POST or request.POST['email'] is '':
        context['first_name'] = first_name
        context['last_name'] = last_name
        context['insurance_company'] = company
        context['insurance_id'] = insurance
        context['register_error'] = "The Email field cannot be blank."
        return render(request, 'register_patient_1.html', context)
    #
    # Validate username is unique
    #
    a = unique_username(request.POST['email'])
    if not a:
        context['register_error'] = "This email is already in use.  Please enter a different email."
        context['first_name'] = first_name
        context['last_name'] = last_name
        context['email'] = email
        context['insurance'] = insurance
        context['company'] = company
        return render(request, 'register_patient_1.html', context)
    #
    # Check existence of other fields
    #
    if 'insurance_company' not in request.POST or request.POST['insurance_company'] is '':
        context['first_name'] = first_name
        context['last_name'] = last_name
        context['email'] = email
        context['insurance'] = insurance
        context['register_error'] = "The Insurance Company field cannot be blank."
        return render(request, 'register_patient_1.html', context)
    if 'insurance_id' not in request.POST is None or request.POST['insurance_id'] is '':
        context['first_name'] = first_name
        context['last_name'] = last_name
        context['email'] = email
        context['company'] = company
        context['register_error'] = "The Insurance ID field cannot be blank."
        return render(request, 'register_patient_1.html', context)
    if not unique_insurance(insurance):
        context['first_name'] = first_name
        context['last_name'] = last_name
        context['email'] = email
        context['company'] = company
        context['register_error'] = "This Insurance ID is already in use."
        return render(request, 'register_patient_1.html', context)
    if not validate_insurance(insurance):
        context['first_name'] = first_name
        context['last_name'] = last_name
        context['email'] = email
        context['company'] = company
        context['register_error'] = "Insurance ID must be 12 alphanumeric characters starting with a letter."
        return render(request, 'register_patient_1.html', context)
    if 'password' not in request.POST or request.POST['password'] is '':
        context['first_name'] = first_name
        context['last_name'] = last_name
        context['company'] = company
        context['insurance'] = insurance
        context['email'] = email
        context['register_error'] = "The Password field cannot be blank."
        return render(request, 'register_patient_1.html', context)
    else:
        # Save data for use in register_step_3
        request.session['email'] = request.POST['email']
        request.session['password'] = request.POST['password']
        request.session['insurance'] = request.POST['insurance_id']
        request.session['company'] = request.POST['insurance_company']
        request.session['first_name'] = first_name
        request.session['last_name'] = last_name
        context['hospitals'] = Hospital.objects.all()
        context['doctors'] = Doctor.objects.all()
        return render(request, 'register_patient_2.html', context)

def more_register(request):
    context = defaultContext(request, "Register")
    if 'cancel' in request.POST:
        return redirect(reverse('index'))
    if request.POST['hospital'] == "-1":
        context['register_error'] = "You must select a hospital."
        context['hospitals'] = Hospital.objects.all()
        return render(request, 'register_patient_2.html', context)
    else:
        h = get_object_or_404(Hospital, pk=request.POST['hospital']).pk
        context['doctors'] = Doctor.objects.filter(hospitals__pk = h)
        request.session['hospital'] = h
        return render(request, 'register_choose_pcp.html', context)

def register_step_3(request):
    context = defaultContext(request, "Register")
    if 'cancel' in request.POST:
        return redirect(reverse('index'))
    else: #'register' in request.POST
        if request.POST['pcp'] == "-1":
            context['register_error'] = "You must select a primary care physician."
            context['doctors'] = Doctor.objects.all()
            return render(request, 'register_patient_2.html', context)
            return render(request, 'register_patient_2.html', context)
        # Get data back out of request.session
        username = request.session['email']
        email = request.session['email']
        password = request.session['password']
        company = request.session['company']
        insurance = request.session['insurance']
        first_name = request.session['first_name']
        last_name = request.session['last_name']
        h = get_object_or_404(Hospital, pk=request.session['hospital'])
        p = get_object_or_404(User, pk=request.POST['pcp']).doctor
        # Build user and log in
        user = User.objects.create_user(username, email=email, password=password)
        patient = Patient()
        user.first_name = first_name
        user.last_name = last_name
        patient.insurance_company = company
        patient.insurance_id = insurance
        patient.pcp = p
        patient.hospital = h
        user.patient = patient
        patient.save()
        user.save()
        user = auth.authenticate(username=username, password=password)
        auth.login(request, user)
        return render(request, 'register_patient_pre_optional.html', context)

# called from register_patient_pre_optional and register_patient_optional
def register_finish(request):
    if not request.POST:
        # How even
        return redirect(reverse('index'))
    context = defaultContext(request, "Register")
    # First two should go to dashboard through index view internal logic
    if 'exit' in request.POST:
        return redirect(reverse('index'))
    if 'cancel' in request.POST:
        return redirect(reverse('index'))
    # Continue from pre_optional means go to optional
    if 'continue' in request.POST:
        return render(request, 'register_patient_optional.html', context)
    if 'register' in request.POST:
        if 'phone' in request.POST and request.POST['phone'] != '':
            if validate_phone(request.POST['phone']):
                request.user.patient.phone = request.POST['phone']
        if request.POST['gender'] != -1:
            request.user.patient.gender = request.POST['gender']
        #
        # If feet and inch must BOTH be valid, or it is an error.
        #
        if 'height_feet' in request.POST and request.POST['height_feet'] != '':
            if 'height_inch' in request.POST and request.POST['height_inch'] != '':
                for char in request.POST['height_feet']:
                    test = True
                    if not char.isdigit():
                        test = False
                        break
                if test:
                    for char in request.POST['height_inch']:
                        test = True
                        if not char.isdigit():
                            test = False
                            break
                    if test:
                        request.user.patient.height = 12 * int(request.POST['height_feet'])
                        request.user.patient.height += int(request.POST['height_inch'])
                    else:
                        context['register_error'] = "Your height must only contain numbers."
                        return render(request, 'register_patient_optional.html', context)
                else:
                    context['register_error'] = "Your height must only contain numbers."
                    return render(request, 'register_patient_optional.html', context)
        if 'weight' in request.POST and request.POST['weight'] != '':
            test = True
            for char in request.POST['weight']:
                if not char.isdigit():
                    test = False
                    break
            if test:
                request.user.patient.weight = request.POST['weight']
            else:
                context['register_error'] = "Your weight must only contain numbers."
                return render(request, 'register_patient_optional.html', context)
        if request.POST['eye_color'] != -1:
            request.user.patient.eye_color = request.POST['eye_color']
        if 'birth_date' in request.POST and request.POST['birth_date'] is not '':
            if validate_dob(request.POST['birth_date']):
                request.user.patient.birth_date = request.POST['birth_date']
            else:
                context['register_error'] = "Your Date of Birth cannot be in the future."
                return render(request, 'register_patient_optional.html', context)
        request.user.save()
        request.user.patient.save()
    return redirect(reverse('index'))

@login_required
@transaction.atomic
def register_doctor(request):
    context=defaultContext(request, "Register Doctor")
    context['display_navbar'] = False
    assert_404(context['user_type'] == 'admin')
    context['hospitals'] = Hospital.objects.all()
    if not request.POST:
        return render(request, 'register_doctor.html', context=context)
    else:
        err = check_post_fields(request.POST, ['email', 'password', \
                                    'first_name', 'last_name'])
        if err is not None:
            context['register_error'] = err
            return render(request, 'register_doctor.html', context=context)

        user = auth.authenticate(username=request.POST['email'], \
                                 password=request.POST['password'])

        if 'hospitals' in request.POST.keys():
            hospitals = request.POST.getlist('hospitals')
        else:
            hospitals = []

        user = User.objects.create_user(request.POST['email'], \
                                  email=request.POST['email'], \
                               password=request.POST['password'], \
                             first_name=request.POST['first_name'], \
                              last_name=request.POST['last_name'])
        doc = Doctor()
        doc.parent = user
        doc.save()
        for hk in hospitals:
            doc.hospitals.add(Hospital.objects.get(pk=hk))

        user.save()
        doc.save()

        log_msg(request.user, "new doctor", \
            "Doctor %s %s with email %s has been added to HealthNet" \
            % (request.POST['first_name'],request.POST['last_name'],request.POST['email']))


        return redirect(reverse('dashboard'))

@login_required
@transaction.atomic
def register_nurse(request):
    context=defaultContext(request, "Register Nurse")
    context['display_navbar'] = False
    assert_404(context['user_type'] == 'admin')
    context['hospitals'] = Hospital.objects.all()
    if not request.POST:
        return render(request, 'register_nurse.html', context=context)
    else:
        err = check_post_fields(request.POST, ['email', 'password', \
                                    'first_name', 'last_name'])
        if err is not None:
            context['register_error'] = err
            return render(request, 'register_nurse.html', context=context)

        user = User.objects.create_user(request.POST['email'], \
                                  email=request.POST['email'], \
                               password=request.POST['password'], \
                             first_name=request.POST['first_name'], \
                              last_name=request.POST['last_name'])
        nur = Nurse()
        nur.parent = user
        nur.hospital = Hospital.objects.get(pk=request.POST['hospital'])

        user.save()
        nur.save()

        log_msg(request.user, "new nurse", \
            "Nurse %s %s with email %s has been added to HealthNet" \
            % (request.POST['first_name'],request.POST['last_name'],request.POST['email']))

        return redirect(reverse('dashboard'))

@login_required
@transaction.atomic
def register_admin(request):
    context=defaultContext(request, "Register Admin")
    context['display_navbar'] = False
    context['here'] = 'register_admin'
    assert_404(context['user_type'] == 'admin')
    return register_admin_body(request,'register_admin.html', context) or redirect(reverse('dashboard'))

@transaction.atomic
def register_admin_begin(request):
    context = defaultContext(request, "Register Initial Admin")
    context['here'] = 'register_admin_begin'
    assert_404(Administrator.objects.all().count() == 0)
    return register_admin_body(request, 'begin.html', context) or login(request)

@transaction.atomic
def register_admin_body(request, template, context):
    if not request.POST:
        return render(request, template, context=context)
    else:
        err = check_post_fields(request.POST, ['email', 'password', \
                                    'first_name', 'last_name'])
        if err is not None:
            context['register_error'] = err
            return render(request, template, context=context)

        user = User.objects.create_user(request.POST['email'], \
                                  email=request.POST['email'], \
                               password=request.POST['password'], \
                             first_name=request.POST['first_name'], \
                              last_name=request.POST['last_name'])
        adm = Administrator()
        adm.parent = user
        user.save()
        adm.save()

        log_msg(request.user, "new admin creation", \
            "Administrator %s %s with email %s has been added to HealthNet" \
                    % (user.first_name,user.last_name,user.email))

        return None

@login_required
@transaction.atomic
def make_hospital(request):
    context = defaultContext(request, "New Hospital")
    assert_404(context['user_type'] == 'admin')
    if not request.POST:
        return render(request, 'make_hospital.html', context=context)
    else:
        err = check_post_fields(request.POST, ['name', 'location'])
        if err is not None:
            context['register_error'] = err
            return render(request, 'make_hospital.html', context=context)

        hospital = Hospital()
        hospital.name = request.POST['name']
        hospital.location = request.POST['location']
        hospital.save()

        log_msg(request.user, "new hospital creation", \
            "A new hospital has been created with a name of \"%s\" and an address of \"%s\"" \
                    % (hospital.name,hospital.location))

        return redirect(reverse('dashboard'))

# ******************************************************************************
# Profile Views
# ******************************************************************************

# This is simply a page that redirects you to your profile, to make the navbar
# at the top easier
@login_required
def profile_redirect(request):
    return redirect(reverse('profile', args=(request.user.pk,)))

@login_required
@transaction.atomic
def profile(request, id):
    context = defaultContext(request, 'Profile')
    markActive('Profile', context)

    active_user = get_object_or_404(User, pk=id)
    if not user_is_patient(active_user):
        #Invalid target error catch
        context['user_type_error'] = "User must be a Patient."
        return render(request, 'dashboard.html', context)

    context['feet'] = (int)(active_user.patient.height/12)
    context['inch'] = (int)(active_user.patient.height%12)

    return render(request, 'profile.html', context)


@login_required
def profile_edit(request, id):
    context = defaultContext(request, 'Profile_edit')
    markActive('profile_edit.html', context)

    active_user = get_object_or_404(User, pk=id)
    if not user_is_patient(active_user):
        context['user_type_error'] = "Only Patient profiles can be edited."
        markActive('dashboard.html', context)
        return render(request, 'dashboard.html', context)
    context['doctors'] = Doctor.objects.all()
    context['user_type'] = user_type_string(request.user)
    context['hospitals'] = Hospital.objects.all()
    context['feet'] = (int)(active_user.patient.height/12)
    context['inch'] = active_user.patient.height%12
    context['year'] = active_user.patient.birth_date.year
    #
    # Date display cleaning
    #
    if active_user.patient.birth_date.month < 10:
        context['month'] = "0" + str(active_user.patient.birth_date.month)
    else:
        context['month'] = active_user.patient.birth_date.month
    if active_user.patient.birth_date.day < 10:
        context['day'] = "0" + str(active_user.patient.birth_date.day)
    else:
        context['day'] = active_user.patient.birth_date.day

    if not request.POST:
        return render(request, 'profile_edit.html', context)
    else:
        if 'confirm' in request.POST:
            #
            # FIRST NAME
            #
            if 'first_name' not in request.POST or request.POST['first_name'] is '':
                # Ignore, it isn't necessary.
                pass
            else:
                if validate_name(request.POST['first_name']):
                    active_user.first_name = request.POST['first_name']
                else:
                    context['first_name_error'] = "Your first name must contain only letters."
                    return render(request, 'profile_edit.html', context)

            #
            # LAST NAME
            #
            if 'last_name' not in request.POST or request.POST['last_name'] is '':
                # Ignore, it isn't necessary
                pass
            else:
                if validate_name(request.POST['last_name']):
                    active_user.last_name = request.POST['last_name']
                else:
                    context['last_name_error'] = "Your last name must contain only letters."
                    return render(request, 'profile_edit.html', context)

            #
            # PHONE NUMBER
            #
            if 'phone' not in request.POST or request.POST['phone'] is '':
                # Ignore, it isn't necessary.
                pass
            else:
                if validate_phone(request.POST['phone']):
                    active_user.patient.phone = request.POST['phone']
                else:
                    context['phone_error'] = "Please enter your complete phone number, with area code."
                    return render(request, 'profile_edit.html', context)

            #
            # INSURANCE COMPANY
            #
            if 'insurance_company' not in request.POST or request.POST['insurance_company'] is '':
                context['COMPANY_error'] = "You must have an Insurance Company."
                return render(request, 'profile_edit.html', context)
            else:
                active_user.patient.insurance_company = request.POST['insurance_company']

            #
            # INSURANCE ID
            #
            if 'insurance_id' not in request.POST or request.POST['insurance_id'] is '':
                    context['ID_error'] = "You must have an Insurance ID."
                    return render(request, 'profile_edit.html', context)
            else:
                if validate_insurance(request.POST['insurance_id']):
                    active_user.patient.insurance_id = request.POST['insurance_id']
                else:
                    context['ID_error'] = "Your Insurance ID must be a letter followed by 11 alphanumeric characters."
                    return render(request, 'profile_edit.html', context)

            # Hospital cannot be absent.
            active_user.patient.hospital = get_object_or_404(Hospital, pk=request.POST['hospital'])
            # Doctor cannot be absent.
            active_user.patient.pcp = get_object_or_404(Doctor, pk=request.POST['doctor'])
            # Gender cannot be absent.
            active_user.patient.gender = request.POST['gender']

            #
            # HEIGHT
            #
            if 'height_feet' in request.POST and request.POST['height_feet'] is not '':
                if 'height_inch' in request.POST and request.POST['height_inch'] is not '':
                    height_temp = (int)(request.POST['height_feet'])*12
                    height_temp += (int)(request.POST['height_inch'])
                    if validate_height(height_temp):
                        active_user.patient.height = height_temp
                    else:
                        context['height_error'] = "Your height cannot be less than 0ft or greater than 9ft."
                        return render(request, 'profile_edit.html', context)
                else:
                    height_temp = (int)(request.POST['height_feet'])*12
                    if validate_height(height_temp):
                        context['height_error'] = "Your height cannot be less than 0ft or greater than 9ft."
                        active_user.patient.height = height_temp
                    else:
                        return render(request, 'profile_edit.html', context)
            else:
                if 'height_inch' in request.POST and request.POST['height_inch'] is not '':
                    context['height_error'] = "Your height must include a feet measurement."
                    return render(request, 'profile_edit.html', context)
                else:
                    pass

            #
            # WEIGHT
            #
            if 'weight' not in request.POST or request.POST['weight'] is '':
                # Ignore, not necessary
                pass
            else:
                if validate_weight(request.POST['weight']):
                    active_user.patient.weight = request.POST['weight']
                else:
                    context['weight_error'] = "Your weight cannot be less than 0lbs or greater than 600lbs."
                    return render(request, 'profile_edit.html', context)

            # eye_color cannot be absent.
            active_user.patient.eye_color = request.POST['eye_color']

            #
            # BIRTH DATE
            #
            if 'birth_date' not in request.POST or request.POST['birth_date'] is '':
                # ignore
                pass
            else:
                if validate_dob(request.POST['birth_date']):
                    active_user.patient.birth_date = request.POST['birth_date']
                else:
                    context['dob_error'] = "Your date of birth cannot be in the future."
                    return render(request, 'profile_edit.html', context)

            active_user.patient.save()
            active_user.save()

            log_msg(request.user, "profile modified", \
                "The profile of %s %s was modified" \
                    % (active_user.first_name,active_user.last_name))

            return redirect(reverse('profile', args=(request.user.pk,)))
        else:
            return redirect(reverse('profile', args=(request.user.pk,)))

# ******************************************************************************
# Calendar Views
# ******************************************************************************

@login_required
def calendar(request):
    context=defaultContext(request, "Calendar")
    markActive('Calendar', context)
    return render(request, 'calendar.html', context=context)

@login_required
def calendar_feed(request):
    start = request.GET['start']
    end = request.GET['end']
    events = Event.objects.filter(attendees=request.user)
    jsonEvents = list(map(lambda e: {
            'id': e.pk,
            'title': e.name,
            'start': e.start.isoformat(),
            'end': e.end.isoformat(),
            'url': reverse('view_appt', args=(e.pk,))
        }, events))
    return JsonResponse({
            'events': jsonEvents,
        })

@login_required
def create_appt(request):
    context = defaultContext(request, "Create Appointment")
    context['display_navbar'] = False

    hospital = None
    title = ""
    attendees = None
    if user_is_patient(request.user):
        if not request.POST:
            if request.user.patient.hospital is None:
                context['create_appt_error'] = "Please pick a hospital on your profile page " \
                                               "before creating an appointment."
                return render(request, 'create_appt.html', context=context)
            if request.user.patient.pcp is None:
                context['create_appt_error'] = "Please pick a primary care physician on your " \
                                               "profile page before creating an appointment."
                return render(request, 'create_appt.html', context=context)
            return render(request, 'create_appt.html', context=context)

        err = check_post_fields(request.POST, ['when', 'duration', 'reason'])
        if err is not None:
            context['create_appt_error'] = err
            return render(request, 'create_appt.html', context=context)

        hospital = request.user.patient.hospital
        attendees = [request.user, request.user.patient.pcp.parent]
        title = "Appointment with Dr. %s and %s %s" % (request.user.patient.pcp.parent.last_name,
                                                         request.user.first_name,
                                                         request.user.last_name)
    else:
        if not request.POST:
            context['hospitals'] = Hospital.objects.all()
            context['doctors'] = Doctor.objects.all()
            context['patients'] = Patient.objects.all()
            context['nurses'] = Nurse.objects.all()
            return render(request, 'create_appt.html', context=context)

        err = check_post_fields(request.POST, ['when', 'duration', 'reason', 'patient', 'doctor'])
        if err is not None:
            context['create_appt_error'] = err
            return render(request, 'create_appt.html', context=context)

        patient = User.objects.get(pk=int(request.POST['patient']))
        doctors = list(map(lambda id: User.objects.get(pk=int(id)), request.POST.getlist('doctor')))

        title = "Appointment with "
        for d in doctors:
            title = title + "Dr. %s, " % (d.last_name)
        title = title + "and %s %s" % (patient.first_name, patient.last_name)

        hospital = patient.patient.hospital

        attendees = doctors.copy()
        attendees.insert(0, patient)
        if 'nurse' in request.POST.keys():
            attendees = attendees + list(map(lambda id: User.objects.get(pk=int(id)), request.POST.getlist('nurse')))

    when_str = request.POST['when']
    duration_str = request.POST['duration']
    reason = request.POST['reason']
    when = datetime.strptime(when_str, "%Y-%m-%dT%H:%M")
    duration = float(duration_str)
    end = when + timedelta(hours=duration)

    for attendee in attendees:
        attendee_events = Event.objects.filter(attendees__exact=attendee)
        for event in attendee_events:
            tz = timezone.get_current_timezone()
            latest_start = max(timezone.make_aware(when,tz), event.start)
            earliest_end = min(timezone.make_aware(end,tz), event.end)
            if latest_start < earliest_end:
                context['create_appt_error'] = "%s %s is busy during that time" % (attendee.first_name,attendee.last_name)
                return render(request, 'create_appt.html', context=context)

    if user_is_patient(request.user) and duration > 0.5:
        context['create_appt_error'] = "You can't create an appointment longer than half an hour."
        return render(request, 'create_appt.html', context=context)

    event = Event(
            name=title,
            start=when,
            end=end,
            location=hospital.name,
            description=reason)
    event.save()
    for a in attendees:
        event.attendees.add(a)

    log_msg(request.user, "new appointment creation", \
            "A new appointment has been created at %s for %s hour(s), with %s" \
                % (when.strftime("%m/%d/%Y %H:%M"), \
                   str(duration_str), \
                   ", ".join("%s %s" % (x.first_name, x.last_name) for x in attendees)))
    return redirect(reverse('view_appt', args=(event.pk,)))

@login_required
def delete_appt(request,id):
    assert_404(request.POST)
    event = get_object_or_404(Event, pk=id)
    if not request.user in event.attendees.all() and user_is_patient(request.user):
        raise PermissionDenied
    log_msg(request.user, "appointment deletion", \
            "An appointment at %s with %s, has been deleted." \
                % (event.start.strftime("%m/%d/%Y %H:%M"), \
                   ", ".join("%s %s" % (x.first_name, x.last_name) for x in event.attendees.all())))
    event.delete()
    return redirect(reverse('calendar'))

@login_required
def view_appt(request, id):
    event = get_object_or_404(Event, pk=id)
    context = defaultContext(request, event.name)
    context['event'] = event
    context['duration'] = (event.end - event.start).total_seconds() / (60 * 60)
    context['appt_id'] = id
    return render(request, 'view_appt.html', context=context)

# ******************************************************************************
# Prescription Views
# ******************************************************************************

@login_required
@transaction.atomic
def create_prescription(request):
    if "Cancel" in request.POST:
        return redirect(reverse('view_prescriptions', args=(request.user.pk,)))
    context = defaultContext(request, 'Prescriptions')
    context = defaultContext(request, 'Create Prescription')
    context['display_navbar'] = False
    context['patients'] = Patient.objects.all()
    context['medications'] = Medication.objects.all()

    if not user_is_doctor(request.user):
        return redirect(reverse('index'))
    if not request.POST:
        return render(request, 'create_prescription.html', context=context)
    else:
        err = check_post_fields(request.POST, ['patient_id', 'drug', 'amount'])
        if err is not None:
            context['create_prescription_error'] = err
            return render(request, 'create_prescription.html', context=context)

        if 'notes' not in request.POST or request.POST['notes'] == '':
            notes = 'None.'
        else:
            notes = request.POST['notes']

    valid = validate_prescription_dates(request.POST['startdate'], request.POST['enddate'])
    if not valid:
        context['create_prescription_error'] = "The start date must be before the end date."
        return render(request, 'create_prescription.html', context=context)

    valid_start = validate_presciption_start(request.POST['startdate'])
    if not valid_start:
        context['create_prescription_error'] = "The start date must be after today."
        return render(request, 'create_prescription.html', context=context)

    tempdrug = get_object_or_404(Medication,pk=int(request.POST['drug']))
    presc = Prescription(
            drug=tempdrug.name,
            amount=request.POST['amount'],
            startdate=request.POST['startdate'],
            enddate=request.POST['enddate'],
            notes=notes,
            patient=get_object_or_404(Patient, pk=request.POST['patient_id']),
            doctor=get_object_or_404(Doctor, pk=request.user.doctor.id))
    presc.save()

    patient = get_object_or_404(User, pk=request.POST['patient_id'])
    log_msg(request.user, "new prescription", \
        "A new prescription of %s has been added for %s %s, starting on %s and ending on %s" \
        % (tempdrug.name,patient.first_name,patient.last_name,request.POST['startdate'],request.POST['enddate']))

    return redirect(reverse('view_prescriptions', args=(request.user.pk,)))

@login_required
def view_prescriptions(request, id):

    context = defaultContext(request, 'Prescriptions')
    markActive('Prescriptions', context)
    presc = None
    if user_is_patient(request.user):
        presc = Prescription.objects.filter(patient_id__exact=request.user.patient.id)
    if user_is_doctor(request.user):
        presc = Prescription.objects.filter(doctor_id__exact=request.user.doctor.id)
    if user_is_nurse(request.user):
        nurse = request.user.nurse
        presc = Prescription.objects.filter(patient__hospital__pk__exact=nurse.hospital.pk)
    context['prescription'] = presc
    if not presc:
        context['user_type_error'] = "There are no prescriptions for you to view at this time."
        return render(request, 'view_prescriptions.html', context)
    return render(request, 'view_prescriptions.html', context)


@login_required
@transaction.atomic
def register_medication(request):
    context=defaultContext(request, 'Register Medication')
    context['display_navbar'] = False
    assert_404(context['user_type'] == 'admin')
    if not request.POST:
        return render(request, 'register_medication.html', context=context)
    else:
        err = check_post_fields(request.POST, ['drug'])
        if err is not None:
            context['register_error'] = err
            return render(request, 'register_medication.html', context=context)
        med = Medication()
        med.name = request.POST['drug']

        med.save()

        log_msg(request.user, "new medication", \
            "A new medication of %s has been added" % (request.POST['drug']))

        return redirect(reverse('dashboard'))

# ******************************************************************************
# Tests & Records Views
# ******************************************************************************

@login_required
def view_medrec(request):
    if user_is_patient(request.user):
        context = defaultContext(request, 'Medical Records')
        context['user_type'] = 'patient'
        p = get_object_or_404(User, pk=request.user.pk).patient
        tests = Test.objects.filter(patient = p)
        context['tests'] = tests
        if not tests:
            context['error_message'] = "There are no tests for you to view at this time."
            return render(request, 'view_medrec.html', context)
        return render(request, 'view_medrec.html', context)
        
    if user_is_nurse(request.user) or user_is_doctor(request.user) or user_is_admin(request.user):
        if not request.POST:
            context = defaultContext(request, "Choose Patient")
            context['patients'] = Patient.objects.all()
            return render(request, 'medrec_choose_patient.html', context)
        context = defaultContext(request, 'Medical Records')
        context['user_type'] = user_type_string(request.user)
        patient = get_object_or_404(Patient, pk=int(request.POST['patient']))
        context['tests'] = Test.objects.filter(patient = patient)
        context['not_patient'] = 'true';
        return render(request, 'view_medrec.html', context)
        
    return Http404("User value is incorrect")

def view_medrec_by_id(request, id):
    context = defaultContext(request, 'Medical Records')
    context['user_type'] = user_type_string(request.user)
    patient = get_object_or_404(Patient, pk=id)
    context['tests'] = Test.objects.filter(patient = patient)
    return render(request, 'view_medrec.html', context)

#@login_required
#def medrec_choose_patient(request):

# @login_required
# def toggle_test_released(request, id):
#     test = Test.objects.get(id)
#     return redirect();

@login_required

def create_test(request):
    context = defaultContext(request, 'Create Test')
    if not request.POST:
        context['doctors'] = Doctor.objects.all()
        context['patients'] = Patient.objects.all()
        if user_is_patient(request.user):
            context['is_patient'] = 'true'
        if user_is_doctor(request.user):
            context['is_doctor'] = 'true'
        return render(request, 'createTest.html', context)

    if user_is_patient(request.user):
        p = request.user.patient
    else:
        patient_name = request.POST['test_patient'].split(' ')
        p = User.objects.filter(first_name = patient_name[0], last_name = patient_name[1])[0].patient

    if user_is_doctor(request.user):
        d = request.user.doctor
    else:
        docname = request.POST['test_doctor'][4:] #remove leading 'Dr. '
        print('doctor name:')
        print(docname)
        d = User.objects.filter(last_name = docname)[0].doctor


    err = check_post_fields(request.POST, ['test_name', 'test_results'])
    if err is not None:
        context['error_message'] = err
        return render(request, 'createTest.html', context=context)

    if request.POST['test_notes'] == '':
        notes = 'none'
    else:
        notes = request.POST['test_notes']

    test = Test(name=request.POST['test_name'], \
             results=request.POST['test_results'], \
               notes=notes, \
              doctor=d, \
             patient=p, \
            released=True)
    test.save();

    log_msg(request.user, "new test", \
        "A test named %s for %s performed by %s has been added" \
        % (request.POST.get('test_name'),request.POST.get('test_patient'),request.POST.get('test_doctor')))

    return redirect(reverse('view_medrec'))

# ******************************************************************************
# Logging Views
# ******************************************************************************


def logging(request):
    if not user_is_admin(request.user):
        return redirect(reverse('dashboard'))
    context=defaultContext(request, 'Activity Log')
    logs = Logging.objects.order_by('-time').all()
    context['logs'] = logs
    return render(request, 'logging.html', context=context)

# ******************************************************************************
# Admission / Discharge Views
# ******************************************************************************

@login_required
def create_admission(request):
    context = defaultContext(request, 'Create Admission')
    assert_404(user_is_doctor(request.user) or user_is_nurse(request.user))
    
    if not request.POST:
        context['patients'] = Patient.objects.all()
        return render(request, 'create_admission.html', context=context)
    
    #error = check_post_fields(request.POST, ['reason'])
    context['error'] = check_post_fields(request.POST, ['reason'])
    a = Admission()
    a.reason = request.POST['reason']
    a.patient = get_object_or_404(Patient, pk=request.POST['patient'])
    a.hospital = a.patient.hospital
    a.save()
    return redirect(reverse('dashboard'))

def delete_admission(request, id):
    Admission.objects.get(id=id).delete()
    return redirect(reverse('dashboard'))

# ******************************************************************************
# System Statistics Views
# ******************************************************************************

@login_required
def view_system_statistics(request):
    context=defaultContext(request, 'System Statistics')
    stats = None
    if not stats:
        context['user_type_error'] = "There are no statistics for you to view at this time."
        return render(request, 'view_system_statistics.html', context)
    return render(request, 'view_system_statistics.html', context=context)

@login_required
@transaction.atomic
def transfer_request(request):
    context = defaultContext(request, 'Request Transfer')
    assert_404(context['user_type'] == 'patient')
    if not request.POST:
        context['hospitals'] = Hospital.objects.exclude(pk=request.user.patient.hospital.pk)
                  
        return render(request, 'transfer_request.html', context=context)
    else:
        assert not check_post_fields(request.POST, ['dest'])
        dest = Hospital.objects.get(id=request.POST['dest'])

        # cancel old requests
        for tr in Transfer.objects.filter(patient=request.user.patient):
            tr.delete()

        Transfer.objects.create(patient=request.user.patient,
                                hospital=dest,
                                time=datetime.now())

        return redirect(reverse('dashboard'))

@login_required
def inbox(request):
    context = defaultContext(request, 'Inbox')

    msgs = []

    transfers = []
    if context['user_type'] == 'doctor':
        for h in request.user.doctor.hospitals.all():
            for trans in Transfer.objects.filter(hospital=h):
                    transfers.append(trans)
    elif context['user_type'] == 'admin':
        transfers = Transfer.objects.all()

    for trans in transfers:
        msgs.append(('Transfer patient "%s" to %s' % (trans.patient.parent.email,
                                                      trans.hospital.name),
                     trans.time,
                     reverse('transfer_view', args=(trans.id,))))

    for msg in Message.objects.filter(dest=request.user):
        msgs.append(('Message from %s: %s' % (msg.src.email, msg.title),
                     msg.time,
                     reverse('message_view', args=(msg.id,))))
                    

    context['msgs'] = sorted(msgs, key=lambda m: m[1])
    context['nmsgs'] = len(msgs)
    
    return render(request, 'inbox.html', context=context)

@login_required
@transaction.atomic
def transfer_view(request, id):
    context = defaultContext(request, 'View Transfer')
    assert_404(context['user_type'] in ['doctor', 'admin'])
    trans = Transfer.objects.get(id=id)
    context['hospital'] = trans.hospital.name
    context['trans_id'] = id

    if request.POST:
        if request.POST['action'] == 'delete':
            trans.delete()
        elif request.POST['action'] == 'confirm':
            trans.patient.hospital = trans.hospital
            trans.patient.save()
            trans.delete()
        return redirect(reverse('dashboard'))

    else:
        return render(request, 'transfer_view.html', context=context)

@login_required
def message_view(request, id):
    msg0 = Message.objects.get(id=id)
    context = defaultContext(request, 'Message %s' % id)
    context['sender'] = msg0.src.email
    context['title'] = msg0.title
    context['body'] = msg0.body
    context['id'] = id

    if request.POST:
        err = check_post_fields(request.POST, ['body'])
        if err:
            context['error'] = err
            return render(request, 'message_view.html', context=context)

        Message.objects.create(src=request.user,
                               dest=msg0.src,
                               time=datetime.now(),
                               title='RE: ' + msg0.title,
                               body=request.POST['body'])

        return redirect(reverse('dashboard'))

    else:
        return render(request, 'message_view.html', context=context)

@login_required
@transaction.atomic
def message_send(request):
    context = defaultContext(request, 'Compose')
    context['recipients'] = filter(lambda u: u.id != request.user.id,
                                   map(lambda u: u.parent,
                                       itertools.chain(
                                           Doctor.objects.all(),
                                           Nurse.objects.all(),
                                           Administrator.objects.all())))

    if request.POST:
        err = check_post_fields(request.POST, ['dest', 'title', 'body'])
        if err:
            context['error'] = err
            return render(request, 'message_send.html', context=context)

        Message.objects.create(src=request.user,
                               dest=User.objects.get(id=request.POST['dest']),
                               time=datetime.now(),
                               title=request.POST['title'],
                               body=request.POST['body'])

        return redirect(reverse('dashboard'))

    else:
        return render(request, 'message_send.html', context=context)

@login_required
def jexport(request):
    assert_404(user_is_admin(request.user))
    return HttpResponse(json_export(), content_type='application/json')

def jimport(request):
    json_import(request.FILES['file'].read().decode('utf-8'))
    return redirect(reverse('index'))
