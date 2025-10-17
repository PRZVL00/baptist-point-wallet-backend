from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'wallets', WalletViewSet)
router.register(r'products', ProductViewSet)
router.register(r'recent-activity', RecentActivityViewSet, basename="recent-activity")
router.register(r'students', StudentViewSet, basename="student")

urlpatterns = [
    path('teacher/stats/', teacher_stats, name='teacher_stats'),
    path('teacher/recent-transactions/', recent_transactions, name='recent_transactions'),
] + router.urls