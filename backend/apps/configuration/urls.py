from django.urls import path

from . import views

app_name = "configuration"

urlpatterns = [
    path("public/", views.PublicConfigurationView.as_view(), name="public"),
    path("site/", views.SiteConfigurationView.as_view(), name="site"),
    path("site/assets/<str:asset>/", views.SiteAssetUploadView.as_view(), name="site-asset-upload"),
    path("seo/", views.SEOConfigurationView.as_view(), name="seo"),
    path("storage/", views.StorageConfigurationView.as_view(), name="storage"),
    path("storage/test/", views.TestStorageConnectionView.as_view(), name="storage-test"),
    path("email/", views.EmailConfigurationView.as_view(), name="email"),
    path("email/test/", views.TestEmailConnectionView.as_view(), name="email-test"),
    path("payment/", views.PaymentConfigurationView.as_view(), name="payment"),
    path("payment/test/", views.TestPaymentConnectionView.as_view(), name="payment-test"),
    path("feature-flags/", views.FeatureFlagsView.as_view(), name="feature-flags"),
]
