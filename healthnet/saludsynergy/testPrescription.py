from django.test import TestCase
from .models import Prescription

class PrescriptionTestCase(TestCase):
    def setUp(self):
        Prescription.objects.create(drug="Syn", amount = "10mg", startdate = 10, enddate = 10, notes = "Some notes.",
                                    patient = "PatientName")

    def test_prescription(self):
        syn = Prescription.objects.get(drug="Syn")
        self.assertEqual(syn, 'The name of this prescription is correct.')