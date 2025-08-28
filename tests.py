from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from .models import Adherent, Ouvrage, Exemplaire

class LoanFlowTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.adherent = Adherent.objects.create(matricule="A001", nom="Doe", prenom="John", role="eleve")
        self.ouvrage = Ouvrage.objects.create(titre="Test Livre")
        self.ex = Exemplaire.objects.create(ouvrage=self.ouvrage, code_barres="CB001", disponible=True)

    def test_create_loan(self):
        url = reverse('pret-create-loan')
        resp = self.client.post('/api/prets/create-loan/', {"exemplaire_id": self.ex.id, "adherent_id": self.adherent.id}, format='json')
        # sans auth, permission denied
        self.assertEqual(resp.status_code, 401)
