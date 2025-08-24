from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from products.views import ProductViewSet, OrderViewSet
from django.conf import settings
from django.conf.urls.static import static

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename="product")
router.register(r'orders', OrderViewSet, basename="order")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
]

# باش تقدر تشوف الصور فـ MEDIA
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
