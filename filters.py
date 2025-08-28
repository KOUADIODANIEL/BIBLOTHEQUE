import django_filters
from .models import Ouvrage, Adherent

class OuvrageFilter(django_filters.FilterSet):
    titre = django_filters.CharFilter(field_name='titre', lookup_expr='icontains')
    auteur = django_filters.CharFilter(field_name='auteur_principal', lookup_expr='icontains')
    theme = django_filters.CharFilter(field_name='theme', lookup_expr='icontains')
    dispo = django_filters.BooleanFilter(method='filter_dispo')

    class Meta:
        model = Ouvrage
        fields = ['titre','auteur_principal','theme']

    def filter_dispo(self, queryset, name, value):
        if value:
            return queryset.filter(exemplaires__disponible=True).distinct()
        return queryset
