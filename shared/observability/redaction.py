"""Redaction helpers for logs and audit records.

Contract only: additive, imported by no live entry point, enforces
nothing at runtime. Rationale: docs/architecture-and-test-environment-plan.md.

Side-effect free and total: pure string/mapping transforms, no I/O, no
client, and no input shape raises.
"""
from __future__ import annotations

import re
from typing import Any, Final, Mapping


REDACTED: Final = "[REDACTED]"

#: Key names whose VALUE is credential material and must never be logged.
SENSITIVE_KEY_NAMES: Final = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "authorization",
        "client_secret",
        # The Flask session cookie is credential material: it is signed
        # with INFO_HARBOR_FLASK_SECRET_KEY (ui/app.py:37-48, IH-027).
        "cookie",
        "id_token",
        "password",
        "private_key",
        "private_key_id",
        "refresh_token",
        "secret",
        "session",
        "set_cookie",
        "token",
    }
)

#: Key names whose VALUE is a raw device identifier or precise personal
#: location. Column names come from the backend-report schema
#: (projects/automation/data_validation.py:36,37,40,41,49): per-device
#: latitude/longitude is the same class of harm as a raw identifier, so
#: it is redacted alongside them.
#:
#: KNOWN over-redaction: POI centroid coordinates use the same column
#: names and are business geometry, not personal data, but they are
#: scrubbed too. Redacting by key name cannot tell the two apart, and
#: guessing wrong on the device side is the more expensive mistake. A
#: caller that needs POI geometry in a log should name the field
#: distinctly (poi_lat / poi_lon) rather than widen this set.
DEVICE_IDENTIFIER_KEY_NAMES: Final = frozenset(
    {
        "devraw",
        "dev_ip",
        "did",
        "idfa",
        "latitude",
        "longitude",
        "udid",
        "udid_idfa",
    }
)

_ALL_SENSITIVE_KEYS: Final = SENSITIVE_KEY_NAMES | DEVICE_IDENTIFIER_KEY_NAMES

# "authorization" is excluded from the BARE key=value rule only. The
# whole-value header rule below already covers `Authorization: <scheme>
# <token>`, and letting the generic rule also match it would redact the
# scheme as if it were the value, then the token separately. It stays in
# the QUOTED rule: `'Authorization': 'Basic ...'` -- the shape requests /
# google-auth put in a logged header dict or traceback -- is NOT
# reachable by the header rule, because a quote sits where that rule
# expects the ":".
_BARE_KV_KEYS: Final = _ALL_SENSITIVE_KEYS - {"authorization"}

# A sensitive key may carry an arbitrary prefix -- GOOGLE_ACCESS_TOKEN,
# SLACK_API_KEY, BQ_CLIENT_SECRET, HTTP_AUTHORIZATION -- and HTTP header
# spellings use "-" where env vars use "_" (X-Api-Key vs API_KEY). Both
# separators have to be handled explicitly: "_" is a word character, so
# \b never fires inside GOOGLE_ACCESS_TOKEN, and "-" does not appear in
# the key names as declared. The trailing guard stops "token_count" from
# matching "token".
_KEY_WITH_PREFIX: Final = (
    r"(?<![A-Za-z0-9_-])(?:[A-Za-z0-9]+[_-])*(?:{alt})(?![A-Za-z0-9_-])"
)


def _key_alternation(names) -> str:
    """Alternation matching each key in its `_` and `-` spellings.

    Longest-first so `access_token` wins over `token` and the trailing
    guard is applied at the true end of the name.
    """
    spellings = set()
    for name in names:
        spellings.add(name)
        spellings.add(name.replace("_", "-"))
    return "|".join(re.escape(n) for n in sorted(spellings, key=len, reverse=True))


_BARE_ALT: Final = _key_alternation(_BARE_KV_KEYS)
_QUOTED_ALT: Final = _key_alternation(_ALL_SENSITIVE_KEYS)

_QUOTED_VALUE: Final = (
    # quoted, allowing backslash escapes so an embedded \" does not end
    # the match early and leave a fragment of the secret behind
    r'"(?:[^"\\]|\\.)*"'
    r"|'(?:[^'\\]|\\.)*'"
    # or a bracketed value: {"token": ["a", "b"]} / {"secret": {"v": x}}.
    # The unquoted fallback stops at the first space, so without these a
    # list or nested object under a sensitive key lost only its FIRST
    # element and printed the rest verbatim. One level of nesting is
    # enough for the shapes that reach a log -- an exception repr or a
    # json.dumps of a request body -- and a regex cannot balance
    # arbitrary depth anyway; redact_mapping() is the correct tool for
    # structured input and handles any depth.
    r"|\[[^\[\]]*\]"
    r"|\{[^{}]*\}"
    # or unquoted: {"token": 12345} / {"api_key": null}
    r"|[^\s,;}\)\]]+"
)

# "key": "value" / 'key': 'value' / "key": 12345 / "key": null
_QUOTED_KV: Final = re.compile(
    r"(?P<prefix>[\"']"
    + _KEY_WITH_PREFIX.format(alt=_QUOTED_ALT)
    + r"[\"']\s*:\s*)(?:"
    + _QUOTED_VALUE
    + r")",
    re.IGNORECASE,
)

# key=value / key: value   (env, query-string and plain-log shapes).
# The value may begin with an already-redacted marker and then keeps
# consuming: that makes re-redaction stable AND stops a value that
# merely starts with the marker from shielding the real secret behind
# it (`token=[REDACTED]hunter2` must not keep "hunter2").
_BARE_KV: Final = re.compile(
    r"(?P<prefix>"
    + _KEY_WITH_PREFIX.format(alt=_BARE_ALT)
    + r"\s*[=:]\s*)"
    + rf"(?P<value>(?=\S)(?:{re.escape(REDACTED)})?[^\s,;&}}\)\]]*)",
    re.IGNORECASE,
)

# Authorization: <scheme> <token> -- the WHOLE header value is credential
# material, so the scheme is redacted along with the token. The header
# name itself survives so a reader can still see what was scrubbed.
# Carries the same PREFIX_ tolerance as the other rules: WSGI/Flask put
# this header in `request.environ` as HTTP_AUTHORIZATION, and a plain \b
# anchor would never match that -- the exact defect fixed for
# GOOGLE_ACCESS_TOKEN. The value stops at a quote so a header inside a
# JSON/dict repr does not swallow the closing delimiter.
_AUTH_HEADER: Final = re.compile(
    r"(?P<prefix>"
    + _KEY_WITH_PREFIX.format(alt=_key_alternation({"authorization"}))
    + r"\s*[=:]\s*)[^,;\n\"']+",
    re.IGNORECASE,
)

# A bare "Bearer <token>" with no Authorization prefix. Bounded so it
# does not eat the closing quote/brace of a surrounding JSON context.
# That bound excludes "]", which is also the last character of the
# redaction marker, so a second pass over `Bearer [REDACTED]` used to
# match `[REDACTED` and re-emit a stray bracket. The marker is therefore
# matched explicitly as a whole, and anything trailing it is consumed --
# `Bearer [REDACTED]leaked` must not keep "leaked".
_BEARER_VALUE_CHAR: Final = r"[^\s\"',;}\)\]]"
_BEARER: Final = re.compile(
    r"(?P<prefix>\bBearer\s+)"
    + rf"(?:{re.escape(REDACTED)}{_BEARER_VALUE_CHAR}*|{_BEARER_VALUE_CHAR}+)",
    re.IGNORECASE,
)

# PEM private-key blocks, including the newline-escaped form that appears
# inside service-account JSON.
_PEM_BLOCK: Final = re.compile(
    r"-----BEGIN[A-Z ]*PRIVATE KEY-----.*?-----END[A-Z ]*PRIVATE KEY-----",
    re.IGNORECASE | re.DOTALL,
)

# A TRUNCATED key block -- a BEGIN marker with no END, which is what a
# cut log line or a clipped exception message actually contains. Without
# this, _PEM_BLOCK does not fire and the generic key=value rule stops at
# the first space, leaving the key body in the log verbatim. Applied
# after _PEM_BLOCK so complete blocks are handled by the tighter rule.
#
# It consumes the marker plus the base64 body that follows it -- NOT the
# rest of the input. The stated use is scrubbing traceback text, and a
# rule anchored to \Z there deletes every frame after the clipped key,
# which destroys exactly the context a responder needs and is how a
# redaction layer earns being switched off. Key material is base64, so
# the body is matched as base64/escaped-newline runs and stops at the
# first line that is not (a traceback frame, a log prefix, a message).
# The body is consumed in code rather than by a repeated regex group:
# a nested quantifier over base64 runs is the classic catastrophic-
# backtracking shape, and this module must stay cheap enough to sit in a
# logging path.
_PEM_BEGIN: Final = re.compile(r"-----BEGIN[A-Z ]*PRIVATE KEY-----", re.IGNORECASE)

#: A whitespace-delimited chunk of key body: base64, optionally carrying
#: the escaped newlines a service-account JSON puts between PEM lines.
#: The length floor separates key material from prose -- an 8-character
#: run of base64 characters directly after a BEGIN marker is body; the
#: words in "more detail follows" or a traceback frame are not.
#:
#: Split into two SINGLE-quantifier patterns on purpose. Writing this as
#: one alternation of repeated runs -- `(?:\\[nr]|[A-Za-z0-9+/=]{8,}|...)+`
#: -- reads naturally and is a nested quantifier: on a long base64 token
#: that cannot reach the anchor, `re` enumerates every way to cut the run
#: into parts of 8 or more, which is exponential. Measured on the
#: module's own stated input (`could not parse -----BEGIN PRIVATE
#: KEY----- <body>",`): 80 characters took 0.23s and 100 took 14.7s. A
#: redaction helper sitting in a logging path must never be the thing
#: that hangs the process, so the two properties are tested separately
#: and each pattern is linear.
_PEM_BODY_CHARS: Final = re.compile(r"[A-Za-z0-9+/=\\-]*")
_PEM_BODY_RUN: Final = re.compile(r"[A-Za-z0-9+/=]{8,}")


def _pem_body_length(token: str) -> int:
    """How much of `token` is key material, from its start.

    A whitespace-delimited token carries whatever punctuation closed the
    surrounding context -- `<body>",` inside a JSON string, `<body>}` in
    a dict repr -- so the body is the leading run of key characters, not
    the whole token. Returns 0 for prose: the length floor is what tells
    a base64 line apart from the words in a traceback frame.
    """
    body = _PEM_BODY_CHARS.match(token).group(0)
    return len(body) if _PEM_BODY_RUN.search(body) else 0


def _redact_truncated_pem(text: str) -> str:
    """Replace every BEGIN marker and the key body that follows it.

    Consumes only the body. A rule anchored to end-of-input deletes
    every traceback frame after a clipped key, which destroys exactly
    the context a responder needs and is how a redaction layer earns
    being switched off.
    """
    out: list[str] = []
    position = 0
    while True:
        match = _PEM_BEGIN.search(text, position)
        if match is None:
            out.append(text[position:])
            return "".join(out)

        out.append(text[position : match.start()])
        out.append(REDACTED)
        cursor = match.end()
        length = len(text)
        while cursor < length:
            # Index scan, not repeated slicing: slicing the remainder to
            # measure leading whitespace is O(remaining) per token, which
            # is quadratic over a long multi-line key body.
            token_start = cursor
            while token_start < length and text[token_start].isspace():
                token_start += 1
            token_end = token_start
            while token_end < length and not text[token_end].isspace():
                token_end += 1
            token = text[token_start:token_end]
            body = _pem_body_length(token)
            if not body:
                break
            cursor = token_start + body
            if body < len(token):
                # The token ended in punctuation that closed the
                # surrounding context, so the key body ends here too.
                break
        position = cursor

# Credential shapes recognisable from the VALUE alone, with no key name
# and no separator. Every rule above needs `key=` or `"key":` context,
# but the commonest logging shape in this repo is an f-string --
# `print(f"using token {t}")` -- which supplies neither. These prefixes
# are issuer-assigned and unambiguous: a Google OAuth access token
# (ya29.), an API key (AIza), an OAuth client secret (GOCSPX-), and a
# refresh token (1//). Anchored on the prefix so ordinary text cannot
# match, and each carries a length floor for the same reason.
_TOKEN_VALUE_SHAPES: Final = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:"
    r"ya29\.[A-Za-z0-9_-]{10,}"
    r"|AIza[A-Za-z0-9_-]{30,}"
    r"|GOCSPX-[A-Za-z0-9_-]{10,}"
    r"|1//[A-Za-z0-9_-]{20,}"
    # A bare JWT, which is what an id_token is. `id_token` is already a
    # declared sensitive key, so only the keyless spelling was missing.
    # Three base64url segments, each with its own length floor, so
    # ordinary dotted text cannot match.
    r"|eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"
    r")"
)

# Legacy key-file paths (settings.py:114-115 records these as LEGACY_*).
_KEY_FILE_PATH: Final = re.compile(r"\bkeys[/\\][\w.\-]+\.json\b", re.IGNORECASE)

# Bare IPv4, which is what dev_ip carries. Octets are bounded to 0-255
# so a version string with an out-of-range or fifth component
# ("2.1.4.300", "1.2.3.4.5") is left alone.
#
# KNOWN over-redaction, accepted deliberately: a four-part version like
# "2.1.4.0" is indistinguishable from an address and is scrubbed. A
# device IP is a personal identifier and a version number is noise, so
# the cost of being wrong is asymmetric. The non-routable placeholders
# below carry no personal information and are exempted, because they
# appear in nearly every bind/health-check line and scrubbing them is
# pure noise -- the kind that gets a redaction layer switched off.
_IPV4_EXEMPT: Final = frozenset({"0.0.0.0", "127.0.0.1", "255.255.255.255"})
_IPV4_OCTET: Final = r"(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])"
_IPV4: Final = re.compile(
    rf"(?<![\w.]){_IPV4_OCTET}(?:\.{_IPV4_OCTET}){{3}}(?![\w.])"
)

#: Env-var names carrying secrets today (ui/app.py:37,54).
_SECRET_ENV_VARS: Final = re.compile(
    r"(?P<prefix>\bINFO_HARBOR_(?:API_TOKEN|FLASK_SECRET_KEY)\s*[=:]\s*)"
    r"(?P<value>[^\s,;]+)",
    re.IGNORECASE,
)


def redact_text(value: Any) -> str:
    """Scrub known credential / device-identifier shapes from text.

    Total: any input is coerced to str and always returns a str.
    Idempotent: redacting already-redacted text returns it unchanged.
    Conservative: only the shapes listed above are touched, so ordinary
    operational detail (project, dataset, campaign code) survives.
    """
    try:
        text = value if isinstance(value, str) else str(value)
    except Exception:  # pragma: no cover - str() on a hostile __str__
        return REDACTED

    text = _PEM_BLOCK.sub(REDACTED, text)
    text = _redact_truncated_pem(text)
    text = _AUTH_HEADER.sub(lambda m: f"{m.group('prefix')}{REDACTED}", text)
    text = _BEARER.sub(lambda m: f"{m.group('prefix')}{REDACTED}", text)
    text = _SECRET_ENV_VARS.sub(lambda m: f"{m.group('prefix')}{REDACTED}", text)
    text = _QUOTED_KV.sub(lambda m: f'{m.group("prefix")}"{REDACTED}"', text)
    text = _BARE_KV.sub(lambda m: f"{m.group('prefix')}{REDACTED}", text)
    text = _TOKEN_VALUE_SHAPES.sub(REDACTED, text)
    text = _KEY_FILE_PATH.sub(REDACTED, text)
    text = _IPV4.sub(
        lambda m: m.group(0) if m.group(0) in _IPV4_EXEMPT else REDACTED, text
    )
    return text


def _suffixed_key(key: Any, index: int) -> Any:
    """Make `key` distinct from an existing one, keeping its type."""
    if isinstance(key, bytes):
        return key + f"_{index}".encode()
    if isinstance(key, tuple):
        return tuple(key) + (f"_{index}",)
    return f"{key}_{index}"


def is_sensitive_key(key: Any) -> bool:
    """True if a mapping key names credential or device-identifier data.

    `bytes` are decoded rather than repr'd: `str(b"password")` is
    `"b'password'"`, which matches nothing, so a bytes key silently
    carried its value through untouched.
    """
    try:
        if isinstance(key, bytes):
            name = key.decode("utf-8", "replace")
        else:
            name = str(key)
        return name.strip().lower() in _ALL_SENSITIVE_KEYS
    except Exception:  # pragma: no cover
        return True


def redact_mapping(record: Any, _depth: int = 0) -> Any:
    """Recursively redact a log/audit record by key name.

    Values under a sensitive key are replaced wholesale; every other
    value is still passed through redact_text() so a secret embedded in
    an otherwise-innocent field (an exception message, say) is caught
    too. Total: non-mapping input is returned via redact_text().
    """
    if _depth > 12:  # defensive bound; audit records are shallow
        return REDACTED

    if isinstance(record, Mapping):
        # .items() is arbitrary user code on a Mapping subclass, and a
        # lazy or remote-backed mapping can raise there. The docstring
        # promises no input shape raises, so a failure here degrades to
        # a redacted marker rather than propagating into a log call --
        # which would turn a logging statement into an outage.
        try:
            items = list(record.items())
        except Exception:  # pragma: no cover - hostile Mapping subclass
            return REDACTED
        out: dict[Any, Any] = {}
        for key, item in items:
            # The KEY is data too. A per-device counter -- the shape an
            # audit record naturally takes -- carries the identifier on
            # the key side, where redacting only values leaves it in the
            # log verbatim: {"203.0.113.42": 7}. A key that survives
            # redact_text() unchanged (a column name, a campaign code)
            # is returned as-is, so ordinary records are untouched.
            # Only str keys are rewritten, so an int or tuple key keeps
            # its type and the record stays usable. A tuple key is
            # recursed into, because a (device_id, date) key carries the
            # identifier just as plainly as a string one does.
            if isinstance(key, str):
                safe_key = redact_text(key)
            elif isinstance(key, bytes):
                safe_key = redact_text(key.decode("utf-8", "replace")).encode()
            elif isinstance(key, tuple):
                safe_key = tuple(
                    redact_text(part) if isinstance(part, str) else part
                    for part in key
                )
            else:
                safe_key = key
            # Collision is checked UNCONDITIONALLY. Guarding it on "the
            # key changed" loses data the other way round: an unredacted
            # key equal to the marker would overwrite the entry a
            # previously redacted key already occupies. The probe walks
            # upward rather than trusting one suffix, since the suffixed
            # form can itself already be taken.
            try:
                taken = safe_key in out
            except Exception:  # pragma: no cover - unhashable/hostile key
                # A Mapping subclass can hand back a key a plain dict
                # never could. The module promises no input shape raises,
                # and a logging path that raises is the outage the
                # items() guard above exists to prevent.
                out[REDACTED] = REDACTED
                continue
            if taken:
                # The suffix keeps the key's own type: downgrading a
                # bytes or tuple key to a str carrying its repr makes the
                # record wrong in a different way.
                index = 1
                while _suffixed_key(safe_key, index) in out:
                    index += 1
                safe_key = _suffixed_key(safe_key, index)
            if is_sensitive_key(key):
                out[safe_key] = REDACTED
            else:
                out[safe_key] = redact_mapping(item, _depth + 1)
        return out

    # A namedtuple has NAMED fields, so it must be redacted by key like a
    # mapping -- treating it as a plain sequence would let a `token` or
    # `private_key` field through untouched. It is also constructed from
    # positional fields, not from a single iterable.
    if isinstance(record, tuple) and hasattr(record, "_fields"):
        try:
            fields = list(record._fields)
        except Exception:  # pragma: no cover - _fields is not a sequence
            fields = []
        # zip() truncates, so a mismatched _fields would silently drop
        # trailing values -- including secret ones. Pad instead, and
        # treat an unnamed position as sensitive.
        if len(fields) < len(record):
            fields += [None] * (len(record) - len(fields))
        values = [
            REDACTED
            if field is None or is_sensitive_key(field)
            else redact_mapping(value, _depth + 1)
            for field, value in zip(fields, record)
        ]
        try:
            return type(record)(*values)
        except Exception:  # pragma: no cover - exotic namedtuple subclass
            return tuple(values)

    if isinstance(record, (list, tuple)):
        cleaned = [redact_mapping(item, _depth + 1) for item in record]
        if not isinstance(record, tuple):
            return cleaned
        try:
            return type(record)(cleaned)
        except Exception:  # pragma: no cover - exotic tuple subclass
            return tuple(cleaned)

    if isinstance(record, (bool, int, float)) or record is None:
        return record

    return redact_text(record)
