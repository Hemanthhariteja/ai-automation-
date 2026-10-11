import re
import secrets

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return slug or "business"


def unique_business_slug(db, base_name: str) -> str:
    """Appends a short random suffix on collision rather than an incrementing
    counter — avoids a race between the uniqueness check and the insert
    under concurrent registrations, and never leaks how many businesses
    already share a name."""
    from app.models.business import Business

    base = slugify(base_name)
    slug = base
    while db.query(Business).filter(Business.slug == slug).first() is not None:
        slug = f"{base}-{secrets.token_hex(2)}"
    return slug
