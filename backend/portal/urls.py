from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
for name, view in [('addresses', views.AddressViewSet), ('services', views.ServiceViewSet), ('areas', views.ServiceAreaViewSet), ('availability', views.AvailabilityViewSet), ('offers', views.OfferViewSet), ('products', views.ProductViewSet), ('bookings', views.BookingViewSet), ('estimates', views.EstimateViewSet), ('stock-movements', views.StockMovementViewSet), ('job-photos', views.JobPhotoViewSet), ('feedback', views.FeedbackViewSet), ('invoices', views.InvoiceViewSet)]:
    router.register(name, view, basename=name)

urlpatterns = [path('config/', views.public_config), path('auth/register/', views.register), path('auth/login/', views.login), path('auth/logout/', views.logout), path('auth/me/', views.me), path('technicians/', views.technicians), path('dashboard/', views.dashboard), path('', include(router.urls))]
