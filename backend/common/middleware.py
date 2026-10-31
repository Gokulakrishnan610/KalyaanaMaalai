from django.middleware.gzip import GZipMiddleware


class CompressMiddleware(GZipMiddleware):
    """Gzips API answers (lists shrink to about a fifth), but never the live-updates stream, which must not be held back."""

    def process_response(self, request, response):
        if response.get("Content-Type", "").startswith("text/event-stream"):
            return response
        return super().process_response(request, response)
