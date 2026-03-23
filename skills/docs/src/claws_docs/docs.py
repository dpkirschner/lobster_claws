"""Google Docs API client module — stub for TDD RED phase."""

import httpx

from claws_common.client import ClawsClient
from claws_common.output import crash, fail


def get_access_token(as_user=None):
    raise NotImplementedError


def extract_text(document):
    raise NotImplementedError


def list_documents(max_results=100, as_user=None):
    raise NotImplementedError


def read_document(doc_id, as_user=None):
    raise NotImplementedError


def create_document(title, body=None, as_user=None):
    raise NotImplementedError


def append_text(doc_id, text, as_user=None):
    raise NotImplementedError


def handle_docs_error(e):
    raise NotImplementedError
