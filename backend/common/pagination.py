from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """20 per page by default; screens that need more (like the board) can ask for ?page_size=200."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200
