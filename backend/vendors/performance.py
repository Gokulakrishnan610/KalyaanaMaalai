"""How a vendor has performed: ratings from planners plus punctuality from wedding-day check-ins."""
from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce

from weddings.models import VendorArrival, VendorRating


def _rating_expr():
    return ExpressionWrapper((F("punctuality") + F("quality") + F("pricing")) * 1.0 / 3, output_field=FloatField())


def with_stats(vendors):
    """Adds avg_rating (mean of the three scores over all weddings) and weddings_count to a Vendor queryset."""
    from quotations.models import WeddingVendor

    rating = (VendorRating.objects.filter(vendor=OuterRef("pk")).order_by().values("vendor")
              .annotate(a=Avg(_rating_expr())).values("a"))
    weddings = (WeddingVendor.objects.filter(vendor=OuterRef("pk")).order_by().values("vendor")
                .annotate(c=Count("pk")).values("c"))
    return vendors.annotate(avg_rating=Subquery(rating, output_field=FloatField()),
                            weddings_count=Coalesce(Subquery(weddings), 0))


def punctuality_for(vendor_ids) -> dict:
    """{vendor_id: {"punctuality_pct", "avg_delay_min", "arrivals"}} from the check-ins M2 records.

    Only arrivals that were judged (ON_TIME or LATE) count. Vendors with none are left out.
    """
    arrivals = VendorArrival.objects.filter(vendor_id__in=list(vendor_ids),
                                            status__in=[VendorArrival.Status.ON_TIME, VendorArrival.Status.LATE])
    counts = arrivals.values("vendor_id").annotate(
        total=Count("pk"), on_time=Count("pk", filter=Q(status=VendorArrival.Status.ON_TIME)))
    result = {}
    for row in counts:
        result[row["vendor_id"]] = {"punctuality_pct": round(100 * row["on_time"] / row["total"], 1),
                                    "arrivals": row["total"], "avg_delay_min": 0.0}
    delays: dict[int, list[float]] = {}
    for vendor_id, expected, arrived in arrivals.filter(arrived_at__isnull=False).values_list(
            "vendor_id", "expected_at", "arrived_at"):
        delays.setdefault(vendor_id, []).append(max(0.0, (arrived - expected).total_seconds() / 60))
    for vendor_id, values in delays.items():
        if vendor_id in result:
            result[vendor_id]["avg_delay_min"] = round(sum(values) / len(values), 1)
    return result


def performance_for(vendor) -> dict:
    """The scorecard: average scores, punctuality from check-ins and one 0-100 score."""
    from quotations.models import WeddingVendor

    ratings = VendorRating.objects.filter(vendor=vendor).aggregate(
        punctuality=Avg("punctuality"), quality=Avg("quality"), pricing=Avg("pricing"), n=Count("pk"))
    check_ins = punctuality_for([vendor.pk]).get(vendor.pk)
    punctuality_pct = check_ins["punctuality_pct"] if check_ins else None

    score = None
    if ratings["n"]:
        # punctuality counts the real check-ins when we have them, the planner's rating otherwise
        punctuality_part = punctuality_pct / 100 if punctuality_pct is not None else ratings["punctuality"] / 5
        score = round(100 * (0.4 * ratings["quality"] / 5 + 0.3 * ratings["pricing"] / 5 + 0.3 * punctuality_part))
    return {
        "avg_quality": _round(ratings["quality"]),
        "avg_pricing": _round(ratings["pricing"]),
        "avg_punctuality_rating": _round(ratings["punctuality"]),
        "punctuality_pct": punctuality_pct,
        "avg_delay_min": check_ins["avg_delay_min"] if check_ins else None,
        "arrivals_counted": check_ins["arrivals"] if check_ins else 0,
        "ratings_count": ratings["n"],
        "weddings_count": WeddingVendor.objects.filter(vendor=vendor).count(),
        "score": score,
    }


def _round(value):
    return None if value is None else round(value, 2)
