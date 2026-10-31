"""How we recognise a client we already have: by client name + email, ignoring capitals and spaces."""
from clients.models import Client


def find_client(client_name: str, email: str) -> Client | None:
    """The client with this name and email, or None. Both must be filled in to count as a match."""
    client_name, email = (client_name or "").strip(), (email or "").strip()
    if not client_name or not email:
        return None
    return Client.objects.filter(client_name__iexact=client_name, email__iexact=email).first()
