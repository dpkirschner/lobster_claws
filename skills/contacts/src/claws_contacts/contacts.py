"""Google Contacts (People API) client module.

Handles token acquisition, contact listing, searching, getting,
creating, updating (with etag), deleting, and error handling.
"""

import httpx
from claws_common.client import ClawsClient
from claws_common.output import crash, fail

AUTH_PORT = 8301
CONTACTS_SCOPE = "https://www.googleapis.com/auth/contacts"
PEOPLE_BASE = "https://people.googleapis.com/v1"
PERSON_FIELDS = "names,emailAddresses,phoneNumbers"


def get_access_token(as_user: str | None = None) -> str:
    """Get Contacts access token from auth server."""
    client = ClawsClient(service="google-auth", port=AUTH_PORT)
    body: dict = {"scopes": [CONTACTS_SCOPE]}
    if as_user:
        body["subject"] = as_user
    resp = client.post_json("/token", body)
    return resp["access_token"]


def _contacts_headers(token: str) -> dict:
    """Build authorization headers for People API calls."""
    return {"Authorization": f"Bearer {token}"}


def _contacts_get(url: str, token: str, params: dict | None = None) -> dict:
    """GET request to People API."""
    resp = httpx.get(
        url,
        params=params,
        headers=_contacts_headers(token),
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def _contacts_post(url: str, token: str, body: dict) -> dict:
    """POST request to People API."""
    resp = httpx.post(
        url,
        json=body,
        headers=_contacts_headers(token),
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def _contacts_patch(url: str, token: str, body: dict, params: dict | None = None) -> dict:
    """PATCH request to People API."""
    resp = httpx.patch(
        url,
        json=body,
        params=params,
        headers=_contacts_headers(token),
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def _contacts_delete(url: str, token: str) -> None:
    """DELETE request to People API."""
    resp = httpx.delete(
        url,
        headers=_contacts_headers(token),
        timeout=30.0,
    )
    resp.raise_for_status()


def list_contacts(max_results: int = 100, as_user: str | None = None) -> list[dict]:
    """List contacts from the user's connections.

    Returns list of person resources from People API.
    """
    token = get_access_token(as_user=as_user)
    data = _contacts_get(
        f"{PEOPLE_BASE}/people/me/connections",
        token,
        params={"personFields": PERSON_FIELDS, "pageSize": max_results},
    )
    return data.get("connections", [])


def search_contacts(
    query: str, max_results: int = 10, as_user: str | None = None
) -> list[dict]:
    """Search contacts by query string.

    Returns list of search result objects from People API.
    """
    token = get_access_token(as_user=as_user)
    data = _contacts_get(
        f"{PEOPLE_BASE}/people:searchContacts",
        token,
        params={"query": query, "readMask": PERSON_FIELDS, "pageSize": max_results},
    )
    return data.get("results", [])


def get_contact(resource_name: str, as_user: str | None = None) -> dict:
    """Get a single contact by resource name (e.g., people/c1234567890)."""
    token = get_access_token(as_user=as_user)
    return _contacts_get(
        f"{PEOPLE_BASE}/{resource_name}",
        token,
        params={"personFields": PERSON_FIELDS},
    )


def create_contact(
    name: str,
    email: str | None = None,
    phone: str | None = None,
    as_user: str | None = None,
) -> dict:
    """Create a new contact with name and optional email/phone."""
    token = get_access_token(as_user=as_user)
    person: dict = {"names": [{"givenName": name}]}
    if email:
        person["emailAddresses"] = [{"value": email}]
    if phone:
        person["phoneNumbers"] = [{"value": phone}]
    return _contacts_post(f"{PEOPLE_BASE}/people:createContact", token, person)


def update_contact(
    resource_name: str,
    name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    as_user: str | None = None,
) -> dict:
    """Update an existing contact. Fetches etag first, then patches.

    Only updates fields that are provided (non-None).
    """
    token = get_access_token(as_user=as_user)

    # Fetch current contact to get etag
    current = _contacts_get(
        f"{PEOPLE_BASE}/{resource_name}",
        token,
        params={"personFields": PERSON_FIELDS},
    )
    etag = current.get("etag", "")

    # Build update body with etag
    person: dict = {"etag": etag}
    update_fields = []

    if name is not None:
        person["names"] = [{"givenName": name}]
        update_fields.append("names")
    if email is not None:
        person["emailAddresses"] = [{"value": email}]
        update_fields.append("emailAddresses")
    if phone is not None:
        person["phoneNumbers"] = [{"value": phone}]
        update_fields.append("phoneNumbers")

    return _contacts_patch(
        f"{PEOPLE_BASE}/{resource_name}:updateContact",
        token,
        person,
        params={"updatePersonFields": ",".join(update_fields)},
    )


def delete_contact(resource_name: str, as_user: str | None = None) -> None:
    """Delete a contact by resource name."""
    token = get_access_token(as_user=as_user)
    _contacts_delete(f"{PEOPLE_BASE}/{resource_name}:deleteContact", token)


def handle_contacts_error(e: httpx.HTTPStatusError) -> None:
    """Translate People API errors to user-friendly messages."""
    try:
        error_data = e.response.json()
        message = error_data.get("error", {}).get("message", str(e))
    except Exception:
        message = str(e)

    status = e.response.status_code
    if status == 401:
        crash(
            "Contacts authentication failed. Token may be expired or delegation misconfigured."
        )
    elif status == 403:
        fail(f"Contacts access denied: {message}")
    elif status == 404:
        fail(f"Contact not found: {message}")
    elif status == 429:
        fail("Contacts rate limit exceeded. Try again later.")
    else:
        crash(f"Contacts API error ({status}): {message}")
