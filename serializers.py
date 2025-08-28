from rest_framework import serializers
from .models import Adherent, Ouvrage, Exemplaire, Pret, Reservation, Penalite

class AdherentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Adherent
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")

class ExemplaireSerializer(serializers.ModelSerializer):
    ouvrage_titre = serializers.ReadOnlyField(source="ouvrage.titre")
    class Meta:
        model = Exemplaire
        fields = "__all__"

class OuvrageSerializer(serializers.ModelSerializer):
    exemplaires = ExemplaireSerializer(many=True, read_only=True)
    disponibilite = serializers.SerializerMethodField()
    class Meta:
        model = Ouvrage
        fields = "__all__"

    def get_disponibilite(self, obj):
        return obj.exemplaires.filter(disponible=True).count()

class PretSerializer(serializers.ModelSerializer):
    exemplaire = ExemplaireSerializer(read_only=True)
    exemplaire_id = serializers.PrimaryKeyRelatedField(queryset=Exemplaire.objects.all(), source="exemplaire", write_only=True)
    adherent = AdherentSerializer(read_only=True)
    adherent_id = serializers.PrimaryKeyRelatedField(queryset=Adherent.objects.all(), source="adherent", write_only=True)

    class Meta:
        model = Pret
        fields = ["id","exemplaire","exemplaire_id","adherent","adherent_id","date_pret","date_echeance","date_retour","renouvellements","statut"]

class ReservationSerializer(serializers.ModelSerializer):
    ouvrage = OuvrageSerializer(read_only=True)
    ouvrage_id = serializers.PrimaryKeyRelatedField(queryset=Ouvrage.objects.all(), source="ouvrage", write_only=True)
    adherent = AdherentSerializer(read_only=True)
    adherent_id = serializers.PrimaryKeyRelatedField(queryset=Adherent.objects.all(), source="adherent", write_only=True)
    class Meta:
        model = Reservation
        fields = "__all__"

class PenaliteSerializer(serializers.ModelSerializer):
    pret = PretSerializer(read_only=True)
    class Meta:
        model = Penalite
        fields = "__all__"
