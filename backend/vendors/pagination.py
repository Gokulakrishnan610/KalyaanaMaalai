from common.pagination import StandardPagination


class VendorPagination(StandardPagination):
    """Accepts ?limit= (as the vendor screens do) as well as ?page_size=."""

    def get_page_size(self, request):
        if "limit" in request.query_params:
            try:
                return max(1, min(int(request.query_params["limit"]), self.max_page_size))
            except ValueError:
                pass
        return super().get_page_size(request)
