import json
from .models import *
from django.db import transaction
import datetime

@transaction.atomic
def json_export():
    res = {}
    hospitals = []
    for h in Hospital.objects.all():
        hospitals.append({'name': h.name, 'addr': h.location})
    res['hospitals'] = hospitals

    doctors = []
    for d in Doctor.objects.all():
        doctors.append({'first_name': d.parent.first_name,
                        'last_name': d.parent.last_name,
                        'middle_name': '',
                        'username': d.parent.email,
                        'email': d.parent.email,
                        'phone': '',
                        'addr': '',
                        'password_hash': d.parent.password,
                        'hospital_ids': list(map(lambda h: h.id, d.hospitals.all())),
                        'patient_ids': list(map(lambda p: p.id, Patient.objects.filter(pcp=d))),
                        'dob': datetime.date.today().isoformat()})
    res['doctors'] = doctors

    patients = []
    for p in Patient.objects.all():
        patients.append({'primary_hospital_id': p.hospital.id,
                         'password_hash': p.parent.password,
                         'weight': p.weight,
                         'last_name': p.parent.last_name,
                         'email': p.parent.email,
                         'phone': p.phone,
                         'username': p.parent.email,
                         'eye_color': p.eye_color,
                         'bloodtype': p.blood_type,
                         'primary_doctor_id': p.pcp.id,
                         'addr': '',
                         'middle_name': '',
                         'first_name': p.parent.first_name,
                         'emergency_contact': '',
                         'dob': p.birth_date.isoformat(),
                         'height': p.height,
                         'doctor_ids': [ p.pcp.id ],
                         'insurance_company': p.insurance_company,
                         'insurance_id': p.insurance_id})
    res['patients'] = patients

    admins = []
    for a in Administrator.objects.all():
        admins.append({'hospital_ids': [],
                       'username': a.parent.email,
                       'password_hash': a.parent.password,
                       'middle_name': '',
                       'last_name': a.parent.last_name,
                       'addr': '',
                       'phone': '',
                       'first_name': a.parent.first_name,
                       'dob': datetime.date.today().isoformat(),
                       'primary_hospital_id': None,
                       'email': a.parent.email})
    res['admins'] = admins

    prescriptions = []
    for p in Prescription.objects.all():
        prescriptions.append({'doctor_id': p.doctor.id,
                              'patient_id': p.patient.id,
                              'notes': p.notes,
                              'name': p.drug,
                              'dosage': p.amount})
    res['prescriptions'] = prescriptions

    appointments = []
    for e in Event.objects.all():
        attnd = list(e.attendees.all())
        appointments.append(
            {'start': e.start,
             'end': e.end,
             'nurse_ids': list(map(lambda u: u.nurse.id, filter(user_is_nurse, attnd))),
             'patient_ids': list(map(lambda u: u.patient.id, filter(user_is_patient, attnd))),
             'doctor_ids': list(map(lambda u: u.doctor.id, filter(user_is_doctor, attnd))),
             'location': e.location,
             'description': "%s: %s" % (e.name, e.description)})
    res['appointments'] = appointments

    nurses = []
    for n in Nurse.objects.all():
        nurses.append({'addr': '',
                       'password_hash': n.parent.password,
                       'middle_name': '',
                       'doctor_ids': [],
                       'last_name': n.parent.last_name,
                       'username': n.parent.email,
                       'phone': '',
                       'first_name': n.parent.first_name,
                       'dob': datetime.date.today().isoformat(),
                       'primary_hospital_id': n.hospital.id,
                       'email': n.parent.email})
    res['nurses'] = nurses

    logs = []
    for l in Logging.objects.all():
        logs.append({'request_secure': True,
                     'user_id': l.user.id if l.user else None,
                     'request_method': '',
                     'request_addr': '',
                     'hospital_id': '',
                     'description': datetime.date.today().isoformat()})
    res['log_entries'] = logs

    tests = []
    for t in Test.objects.all():
        tests.append({'date': datetime.date.today().isoformat(),
                      'doctor_id': t.doctor.id,
                      'results': t.results,
                      'description': t.notes,
                      'released': t.released,
                      'patient_id': t.patient.id,
                      'name': t.name})
    res['tests'] = tests

    return json.dumps(res)

@transaction.atomic
def json_import(string):
    inp = json.loads(string)

    for h in inp['hospitals']:
        Hospital.objects.create(name=h['name'], location=h['addr'])

    for d in inp['doctors']:
        u = User(first_name=d['first_name'], last_name=d['last_name'],
                 username=d['email'], email=d['email'])
        u.password = d['password_hash']
        u.save()

        d1 = Doctor(parent=u)
        d1.save()
        for h in d['hospital_ids']:
            d1.hospitals.add(Hospital.objects.get(pk=h))
        d1.save()

    for n in inp['nurses']:
        u = User(first_name=n['first_name'], last_name=n['last_name'],
                 username=n['email'], email=n['email'])
        u.password = n['password_hash']
        u.save()

        n1 = Nurse(parent=u, hospital=Hospital.objects.get(pk=n['primary_hospital_id']))
        n1.save()

    for p in inp['patients']:
        u = User(first_name=p['first_name'], last_name=p['last_name'],
                 username=p['email'], email=p['email'])
        u.password = p['password_hash']
        u.save()

        p1 = Patient(parent=u, phone=p['phone'], insurance_company=p['insurance_company'],
                     insurance_id=p['insurance_id'], 
                     hospital=Hospital.objects.get(pk=p['primary_hospital_id']),
                     pcp=Doctor.objects.get(pk=p['primary_doctor_id']) if p['primary_doctor_id'] else None,
                     gender=Patient.GENDER_OTHER, height=p['height'], weight=p['weight'],
                     eye_color=p['eye_color'], blood_type=p['bloodtype'],
                     birth_date=p['dob'])
        p1.save()

    for a in inp['admins']:
        u = User(first_name=a['first_name'], last_name=a['last_name'],
                 username=a['email'], email=a['email'])
        u.password = a['password_hash']
        u.save()

        a1 = Administrator(parent=u)
        a1.save()

    for p in inp['prescriptions']:
        p1 = Prescription(drug=p['name'], amount=p['dosage'], startdate=datetime.date.today(),
                          enddate=datetime.date.today(), notes=p['notes'],
                          patient=Patient.objects.get(pk=p['patient_id']),
                          doctor=Doctor.objects.get(pk=p['doctor_id']))
        p1.save()

    for t in inp['tests']:
        t1 = Test(name=t['name'], results=t['results'], notes=t['description'],
                  doctor=Doctor.objects.get(t['doctor_id']),
                  patient=Patient.objects.get(t['patient_id']),
                  released=t['released'])
        t1.save()

    for a in inp['appointments']:
        e = Event(name='Appointment', start=a['start'], end=a['end'],
                  location=a['location'], description=a['description'])

        for d in a['doctor_ids']:
            e.attendees.add(Doctor.objects.get(pk=d).parent)
        for p in a['patient_ids']:
            e.attendees.add(Patient.objects.get(pk=p).parent)
        for n in a['nurse_ids']:
            e.attendees.add(Nurse.objects.get(pk=n).parent)
                        
        e.save()

    for l in inp['log_entries']:
        l1 = Logging(time=datetime.date.today(), title='Imported Log',
                     user=User.objects.get(id=l['user_id']) if l['user_id'] else None,
                     description=l['description'])

        





    
