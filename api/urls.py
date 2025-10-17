from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'wallets', WalletViewSet)
router.register(r'products', ProductViewSet)
router.register(r'recent-activity', RecentActivityViewSet, basename="recent-activity")
router.register(r'students', StudentViewSet, basename="student")

urlpatterns = router.urls
