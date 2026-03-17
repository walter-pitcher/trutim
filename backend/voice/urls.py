"""
Voice Control API URLs.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('profiles', views.VoiceProfileViewSet, basename='voice-profile')
router.register('commands/log', views.VoiceCommandLogViewSet, basename='voice-command-log')
router.register('models', views.KeywordSpotterModelViewSet, basename='kws-model')
router.register('datasets', views.TrainingDatasetViewSet, basename='training-dataset')
router.register('sessions', views.VoiceSessionViewSet, basename='voice-session')

urlpatterns = [
    path('execute/', views.VoiceCommandView.as_view(), name='voice-execute'),
    path('system/', views.VoiceSystemInfoView.as_view(), name='voice-system-info'),
    path('train/', views.TrainModelView.as_view(), name='voice-train'),
    path('generate-data/', views.GenerateDataView.as_view(), name='voice-generate-data'),
    path('', include(router.urls)),
]
