from fastapi import Response


def xml(body: str) -> Response:
    """Wraps a TwiML string in an XML response."""
    return Response(content=body, media_type="application/xml")
