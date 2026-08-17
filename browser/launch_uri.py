from urllib.parse import urlsplit, parse_qsl, urlencode, urlunsplit

LAUNCH_URI_SCHEME = "cgpshell"


def find_launch_uri(argv: list[str]) -> str | None:
    return next((arg for arg in argv if 
                 arg.startswith(f"{LAUNCH_URI_SCHEME}://")),None)


def build_exam_url(exam_url: str, launch_uri: str | None) -> str:
    """
    Returns exam_url rewritten to /exam/{assignment_id} (matching the
    frontend's real routing structure) with every other query param from
    launch_uri appended -- SSO tokens, skill/career_path/level metadata,
    everything except assignment_id itself, which becomes part of the path
    instead of staying a query param.

    Returns exam_url unchanged if launch_uri is None, carries no query
    params, or has no assignment_id (falls back to whatever root page
    exam_url already points at).
    """
    if launch_uri is None:
        return exam_url

    launch_params = dict(parse_qsl(urlsplit(launch_uri).query))
    if not launch_params:
        return exam_url

    assignment_id = launch_params.pop("assignment_id", None)

    parts = urlsplit(exam_url)
    path = f"/exam/{assignment_id}" if assignment_id else parts.path

    existing_params = parse_qsl(parts.query)
    merged_query = urlencode(existing_params + list(launch_params.items()))

    return urlunsplit((parts.scheme, parts.netloc, path, merged_query, parts.fragment))