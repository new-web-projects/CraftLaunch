from django.urls import path

from . import views

app_name = "configuration"

urlpatterns = [
    path("public/", views.PublicConfigurationView.as_view(), name="public"),
    path("site/", views.SiteConfigurationView.as_view(), name="site"),
    path("site/assets/<str:asset>/", views.SiteAssetUploadView.as_view(), name="site-asset-upload"),
    path("seo/", views.SEOConfigurationView.as_view(), name="seo"),
    path("storage/", views.StorageConfigurationView.as_view(), name="storage"),
    path("email/", views.EmailConfigurationView.as_view(), name="email"),
    path("payment/", views.PaymentConfigurationView.as_view(), name="payment"),
    path("feature-flags/", views.FeatureFlagsView.as_view(), name="feature-flags"),
]