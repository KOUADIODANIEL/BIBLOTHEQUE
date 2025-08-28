from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OuvrageViewSet, ExemplaireViewSet, AdherentViewSet, PretViewSet, ReservationViewSet, PenaliteViewSet

router = DefaultRouter()
router.register(r'ouvrages', OuvrageViewSet, basename='ouvrage')
router.register(r'exemplaires', ExemplaireViewSet, basename='exemplaire')
router.register(r'adherents', AdherentViewSet, basename='adherent')
router.register(r'prets', PretViewSet, basename='pret')
router.register(r'reservations', ReservationViewSet, basename='reservation')
router.register(r'penalites', PenaliteViewSet, basename='penalite')

urlpatterns = [
    path("", include(router.urls)),
]
