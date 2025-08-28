from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Adherent(models.Model):
    ROLE_CHOICES = (("eleve", "Élève"), ("enseignant", "Enseignant"))
    matricule = models.CharField(max_length=50, unique=True)
    nom = models.CharField(max_length=150)
    prenom = models.CharField(max_length=150, blank=True)
    date_naissance = models.DateField(null=True, blank=True)
    classe = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    tel = models.CharField(max_length=30, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="eleve")
    actif = models.BooleanField(default=True)
    consentement_rgpd_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.matricule} - {self.nom} {self.prenom or ''}"

class Ouvrage(models.Model):
    isbn = models.CharField(max_length=20, blank=True, null=True)
    titre = models.CharField(max_length=300)
    auteur_principal = models.CharField(max_length=300, blank=True, null=True)
    auteurs = models.TextField(blank=True, null=True)
    editeur = models.CharField(max_length=200, blank=True, null=True)
    annee = models.PositiveIntegerField(null=True, blank=True)
    theme = models.CharField(max_length=150, blank=True, null=True)
    cote = models.CharField(max_length=50, blank=True, null=True)
    resume = models.TextField(blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.titre

class Exemplaire(models.Model):
    ETAT_CHOICES = (("bon","Bon"), ("use","Usé"), ("degrade","Dégradé"))
    ouvrage = models.ForeignKey(Ouvrage, related_name="exemplaires", on_delete=models.CASCADE)
    code_barres = models.CharField(max_length=100, unique=True)
    etat = models.CharField(max_length=20, choices=ETAT_CHOICES, default="bon")
    localisation = models.CharField(max_length=100, blank=True, null=True)
    disponible = models.BooleanField(default=True)
    date_achat = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.ouvrage.titre} [{self.code_barres}]"

class Pret(models.Model):
    STATUT_CHOICES = (("en_cours","En cours"), ("retard","Retard"), ("clos","Clos"))
    exemplaire = models.ForeignKey(Exemplaire, related_name="prets", on_delete=models.PROTECT)
    adherent = models.ForeignKey(Adherent, related_name="prets", on_delete=models.PROTECT)
    date_pret = models.DateTimeField(default=timezone.now)
    date_echeance = models.DateTimeField()
    date_retour = models.DateTimeField(null=True, blank=True)
    renouvellements = models.PositiveIntegerField(default=0)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="en_cours")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def mark_returned(self, returned_at=None):
        returned_at = returned_at or timezone.now()
        self.date_retour = returned_at
        self.statut = "clos"
        self.exemplaire.disponible = True
        self.exemplaire.save()
        self.save()

    def __str__(self):
        return f"Prêt {self.id} - {self.exemplaire} -> {self.adherent}"

class Reservation(models.Model):
    STATUT = (("en_file","En file"), ("notifie","Notifié"), ("retire","Retiré"), ("expire","Expiré"))
    ouvrage = models.ForeignKey(Ouvrage, related_name="reservations", on_delete=models.CASCADE)
    adherent = models.ForeignKey(Adherent, related_name="reservations", on_delete=models.CASCADE)
    rang = models.PositiveIntegerField(default=0)
    statut = models.CharField(max_length=20, choices=STATUT, default="en_file")
    created_at = models.DateTimeField(auto_now_add=True)
    expire_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("rang", "created_at")

    def __str__(self):
        return f"Reservation {self.id} - {self.ouvrage} by {self.adherent}"

class Penalite(models.Model):
    TYPE = (("retard","Retard"), ("perte","Perte"), ("degradation","Dégradation"))
    pret = models.ForeignKey(Pret, related_name="penalites", on_delete=models.CASCADE, null=True, blank=True)
    adherent = models.ForeignKey(Adherent, related_name="penalites", on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=TYPE)
    montant = models.DecimalField(max_digits=8, decimal_places=2)
    solde = models.DecimalField(max_digits=8, decimal_places=2)
    statut_regle = models.BooleanField(default=False)
    regle_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def mark_regle(self):
        self.statut_regle = True
        self.solde = 0
        self.regle_at = timezone.now()
        self.save()
