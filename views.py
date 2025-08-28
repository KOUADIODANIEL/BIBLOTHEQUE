from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from .models import Adherent, Ouvrage, Exemplaire, Pret, Reservation, Penalite
from .serializers import AdherentSerializer, OuvrageSerializer, ExemplaireSerializer, PretSerializer, ReservationSerializer, PenaliteSerializer
from .permissions import IsAdminOrReadOnly

# Paramètres métiers (ex. configurable via model Parametrage)
DEFAULT_LOAN_DURATIONS = {"eleve": 14, "enseignant": 28}  # jours
MAX_LOANS = {"eleve": 3, "enseignant": 5}
MAX_RENEWALS = {"eleve": 1, "enseignant": 2}
DAILY_FINE = 0.5  # unité monétaire / jour ; ex: 0.5 -> 0.5 currency unit

class OuvrageViewSet(viewsets.ModelViewSet):
    queryset = Ouvrage.objects.all().prefetch_related("exemplaires")
    serializer_class = OuvrageSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = None
    filterset_fields = ['theme', 'annee']
    search_fields = ['titre','auteur_principal','auteurs','cote','isbn']

class ExemplaireViewSet(viewsets.ModelViewSet):
    queryset = Exemplaire.objects.all().select_related("ouvrage")
    serializer_class = ExemplaireSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['code_barres','ouvrage__titre','ouvrage__cote']

class AdherentViewSet(viewsets.ModelViewSet):
    queryset = Adherent.objects.all()
    serializer_class = AdherentSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['nom','prenom','matricule','classe']

class PretViewSet(viewsets.ModelViewSet):
    queryset = Pret.objects.all().select_related("exemplaire","adherent")
    serializer_class = PretSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        # si non staff, limiter aux propres prêts si mapping user->adherent existait
        return qs

    @action(detail=False, methods=["post"], url_path="create-loan")
    @transaction.atomic
    def create_loan(self, request):
        """
        payload: { "exemplaire_id": int, "adherent_id": int }
        effectue validation (disponibilité, plafond), enregistre le prêt et rend exemplaire non dispo.
        """
        exemplaire_id = request.data.get("exemplaire_id")
        adherent_id = request.data.get("adherent_id")
        if not exemplaire_id or not adherent_id:
            return Response({"detail":"exemplaire_id and adherent_id are required"}, status=400)
        try:
            exemplaire = Exemplaire.objects.select_for_update().get(pk=exemplaire_id)
        except Exemplaire.DoesNotExist:
            return Response({"detail":"Exemplaire not found"}, status=404)
        if not exemplaire.disponible:
            return Response({"detail":"Exemplaire not available"}, status=400)
        adherent = Adherent.objects.get(pk=adherent_id)
        # contrôle plafond
        loans_count = Pret.objects.filter(adherent=adherent, statut="en_cours").count()
        max_allowed = MAX_LOANS.get(adherent.role, 3)
        if loans_count >= max_allowed:
            return Response({"detail":"Plafond d'emprunt atteint"}, status=400)
        # calcul échéance
        days = DEFAULT_LOAN_DURATIONS.get(adherent.role, 14)
        date_echeance = timezone.now() + timezone.timedelta(days=days)
        pret = Pret.objects.create(exemplaire=exemplaire, adherent=adherent, date_echeance=date_echeance)
        exemplaire.disponible = False
        exemplaire.save()
        serializer = PretSerializer(pret)
        return Response(serializer.data, status=201)

    @action(detail=True, methods=["post"], url_path="return")
    @transaction.atomic
    def return_item(self, request, pk=None):
        """
        mark retour, calcul pénalité si retard, set exemplaire.disponible = True
        """
        try:
            pret = Pret.objects.select_for_update().get(pk=pk)
        except Pret.DoesNotExist:
            return Response({"detail":"Pret not found"}, status=404)
        if pret.statut == "clos":
            return Response({"detail":"Pret already closed"}, status=400)
        now = timezone.now()
        pret.date_retour = now
        # calcul retard
        if pret.date_echeance and now > pret.date_echeance:
            delta = now.date() - pret.date_echeance.date()
            nb_jours = delta.days
            montant = nb_jours * DAILY_FINE
            penalite = Penalite.objects.create(pret=pret, adherent=pret.adherent, type="retard", montant=montant, solde=montant)
        pret.statut = "clos"
        pret.exemplaire.disponible = True
        pret.exemplaire.save()
        pret.save()
        return Response(PretSerializer(pret).data)

    @action(detail=True, methods=["post"], url_path="renew")
    @transaction.atomic
    def renew(self, request, pk=None):
        try:
            pret = Pret.objects.select_for_update().get(pk=pk)
        except Pret.DoesNotExist:
            return Response({"detail":"Pret not found"}, status=404)
        adherent = pret.adherent
        # vérif réservations existantes sur ouvrage
        if Reservation.objects.filter(ouvrage=pret.exemplaire.ouvrage, statut="en_file").exists():
            return Response({"detail":"Impossible de renouveler. Des réservations existent."}, status=400)
        max_renew = MAX_RENEWALS.get(adherent.role, 1)
        if pret.renouvellements >= max_renew:
            return Response({"detail":"Limite de renouvellement atteinte"}, status=400)
        # appliquer renouvellement: décale date_echeance
        days = DEFAULT_LOAN_DURATIONS.get(adherent.role, 14)
        pret.date_echeance = pret.date_echeance + timezone.timedelta(days=days)
        pret.renouvellements += 1
        pret.save()
        return Response(PretSerializer(pret).data)

class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.all().select_related("ouvrage","adherent")
    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # determine rang : last +1
        ouvrage = serializer.validated_data["ouvrage"]
        last = Reservation.objects.filter(ouvrage=ouvrage, statut="en_file").order_by("-rang").first()
        rang = (last.rang + 1) if last else 1
        serializer.save(rang=rang)

    @action(detail=True, methods=["post"], url_path="notify")
    def notify(self, request, pk=None):
        # set statut notifie, set expire_at
        reservation = self.get_object()
        reservation.statut = "notifie"
        # expire dans 48h par défaut
        expire = timezone.now() + timezone.timedelta(hours=48)
        reservation.expire_at = expire
        reservation.save()
        # TODO: envoyer email/sms réel via service d'email
        return Response(ReservationSerializer(reservation).data)

    @action(detail=True, methods=["post"], url_path="expire")
    def expire(self, request, pk=None):
        reservation = self.get_object()
        reservation.statut = "expire"
        reservation.save()
        # gérer le passage au suivant
        return Response(ReservationSerializer(reservation).data)

class PenaliteViewSet(viewsets.ModelViewSet):
    queryset = Penalite.objects.all().select_related("pret","adherent")
    serializer_class = PenaliteSerializer
    permission_classes = [IsAdminOrReadOnly]

    @action(detail=True, methods=["post"], url_path="regler")
    def regler(self, request, pk=None):
        penalite = self.get_object()
        if penalite.statut_regle:
            return Response({"detail":"Déjà réglé"}, status=400)
        # pour MVP: marquer comme réglé
        penalite.mark_regle()
        return Response(PenaliteSerializer(penalite).data)
