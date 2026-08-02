from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole

from .models import Package, ServiceCategory, Tag, Technology, WebsiteCategory, WebsiteFeature, WebsiteType
from .serializers import (
    PackageDetailSerializer,
    PackageListSerializer,
    PackageWriteSerializer,
    ServiceCategorySerializer,
    TagSerializer,
    TechnologySerializer,
    WebsiteCategorySerializer,
    WebsiteFeatureSerializer,
    WebsiteTypeSerializer,
)
from .services import PackageService


class _ActiveLookupListView(generics.ListAPIView):
    """Shared shape for the simple public lookup endpoints — all of
    them are just "list the active rows, admins manage them
    elsewhere"."""

    permission_classes = [AllowAny]
    pagination_class = None  # small, fixed-ish lists — pagination adds nothing here


class ServiceCategoryListView(_ActiveLookupListView):
    queryset = ServiceCategory.objects.active()
    serializer_class = ServiceCategorySerializer


class WebsiteCategoryListView(_ActiveLookupListView):
    queryset = WebsiteCategory.objects.active()
    serializer_class = WebsiteCategorySerializer


class WebsiteTypeListView(_ActiveLookupListView):
    queryset = WebsiteType.objects.active()
    serializer_class = WebsiteTypeSerializer


class TechnologyListView(_ActiveLookupListView):
    queryset = Technology.objects.active()
    serializer_class = TechnologySerializer


class TagListView(_ActiveLookupListView):
    queryset = Tag.objects.active()
    serializer_class = TagSerializer


class WebsiteFeatureListView(_ActiveLookupListView):
    queryset = WebsiteFeature.objects.active()
    serializer_class = WebsiteFeatureSerializer


class PackageListView(generics.ListAPIView):
    """
    GET /api/catalog/packages/ — public, published packages only.
    Filtering/sorting-ready per the spec: ?service_category=<id>,
    ?tier=BASIC, ?technologies=<id>, ?tags=<id>,
    ?ordering=starting_price / -starting_price / delivery_days.
    """

    permission_classes = [AllowAny]
    serializer_class = PackageListSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["service_category", "tier", "technologies", "tags"]
    ordering_fields = ["starting_price", "delivery_days", "created_at"]
    ordering = ["service_category", "starting_price"]
    search_fields = ["name", "description"]

    def get_queryset(self):
        return (
            Package.objects.published()
            .select_related("service_category")
            .prefetch_related("technologies", "tags")
        )


class PackageDetailView(generics.RetrieveAPIView):
    """GET /api/catalog/packages/<slug>/ — public. 404s for
    non-published packages rather than 403, so an unpublished
    package's existence isn't revealed to anonymous visitors."""

    permission_classes = [AllowAny]
    serializer_class = PackageDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Package.objects.published()
            .select_related("service_category")
            .prefetch_related("technologies", "tags", "package_features__website_feature")
        )


class PackageAdminListCreateView(generics.ListCreateAPIView):
    """Admin-only: full CRUD surface (list/create here; retrieve/
    update/delete below), including unpublished and hidden packages."""

    permission_classes = [IsAuthenticated, IsAdminRole]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["service_category", "tier", "status", "visibility"]
    ordering_fields = ["starting_price", "created_at"]

    def get_queryset(self):
        return Package.all_objects.select_related("service_category").prefetch_related(
            "technologies", "tags"
        )

    def get_serializer_class(self):
        return PackageWriteSerializer if self.request.method == "POST" else PackageListSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class PackageAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsAdminRole]
    queryset = Package.all_objects.all()

    def get_serializer_class(self):
        return PackageWriteSerializer if self.request.method in ("PUT", "PATCH") else PackageDetailSerializer

    def perform_destroy(self, instance):
        PackageService.delete(instance, actor=self.request.user)


class PackagePublishView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request, pk):
        package = generics.get_object_or_404(Package.all_objects, pk=pk)
        PackageService.publish(package, actor=request.user)
        return Response(PackageDetailSerializer(package).data, status=status.HTTP_200_OK)


class PackageHideView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request, pk):
        package = generics.get_object_or_404(Package.all_objects, pk=pk)
        PackageService.hide(package, actor=request.user)
        return Response(PackageDetailSerializer(package).data, status=status.HTTP_200_OK)