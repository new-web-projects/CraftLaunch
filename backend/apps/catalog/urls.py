from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("service-categories/", views.ServiceCategoryListView.as_view(), name="service-categories"),
    path("website-categories/", views.WebsiteCategoryListView.as_view(), name="website-categories"),
    path("website-types/", views.WebsiteTypeListView.as_view(), name="website-types"),
    path("technologies/", views.TechnologyListView.as_view(), name="technologies"),
    path("tags/", views.TagListView.as_view(), name="tags"),
    path("website-features/", views.WebsiteFeatureListView.as_view(), name="website-features"),
    path("packages/", views.PackageListView.as_view(), name="packages"),
    path("packages/<slug:slug>/", views.PackageDetailView.as_view(), name="package-detail"),
    path("admin/packages/", views.PackageAdminListCreateView.as_view(), name="admin-packages"),
    path("admin/packages/<int:pk>/", views.PackageAdminDetailView.as_view(), name="admin-package-detail"),
    path("admin/packages/<int:pk>/publish/", views.PackagePublishView.as_view(), name="admin-package-publish"),
    path("admin/packages/<int:pk>/hide/", views.PackageHideView.as_view(), name="admin-package-hide"),
]