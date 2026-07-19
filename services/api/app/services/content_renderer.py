"""Sandboxed Jinja2 renderer, platform-specific renderers, length calculator, UTM generator."""

import re
from dataclasses import dataclass, field
from typing import Any

from jinja2 import BaseLoader, Environment, TemplateNotFound
from jinja2.sandbox import SandboxedEnvironment

from app.config import get_settings
from app.models import ProviderEnum


# ─── Platform capability limits ─────────────────────────────────────

PLATFORM_LIMITS: dict[str, dict[str, int]] = {
    "instagram": {
        "caption_max_length": 2200,
        "hashtag_max_count": 30,
        "hashtag_max_length": 2200,
    },
    "x": {
        "post_max_length": 280,
        "media_attachment_limit": 4,
    },
    "mock": {
        "post_max_length": 10000,
        "caption_max_length": 10000,
    },
}


# ─── Allow-listed Jinja2 globals ────────────────────────────────────

ALLOWED_GLOBALS: dict[str, Any] = {
    "range": range,
    "dict": dict,
    "list": list,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "len": len,
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
    "join": ", ".join,
    "first": lambda seq: seq[0] if seq else None,
    "last": lambda seq: seq[-1] if seq else None,
    "lower": lambda s: s.lower() if s else "",
    "upper": lambda s: s.upper() if s else "",
    "title": lambda s: s.title() if s else "",
    "capitalize": lambda s: s.capitalize() if s else "",
    "truncate": lambda s, l: (s[:l - 3] + "...") if len(s) > l else s,
    "default": lambda v, d: v if v else d,
    "urlencode": lambda s: __import__("urllib.parse").parse.quote(s) if s else "",
}


# ─── Render result ──────────────────────────────────────────────────


@dataclass
class RenderResult:
    title: str | None = None
    body: str = ""
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ─── Template variable extractor ────────────────────────────────────


def extract_variables(template_text: str) -> list[str]:
    if not template_text:
        return []
    pattern = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\|?\s*[^}]*\}\}")
    return sorted(set(pattern.findall(template_text)))


def validate_variables(
    template_text: str,
    allowed_variables: set[str],
) -> tuple[list[str], list[str]]:
    used = extract_variables(template_text)
    unknown = [v for v in used if v not in allowed_variables]
    missing = [v for v in allowed_variables if v not in used]
    return unknown, missing


# ─── Sandboxed renderer ────────────────────────────────────────────


def _make_sandbox_env() -> SandboxedEnvironment:
    env = SandboxedEnvironment(
        loader=BaseLoader(),
        autoescape=False,
    )
    env.globals.update(ALLOWED_GLOBALS)
    return env


_sandbox_env = _make_sandbox_env()


def render_template(
    body_template: str,
    variables: dict[str, Any],
    title_template: str | None = None,
) -> RenderResult:
    result = RenderResult()
    warnings: list[str] = []
    errors: list[str] = []

    allowed_set = set(variables.keys())

    unknown, _ = validate_variables(body_template, allowed_set)
    for v in unknown:
        warnings.append(f"Variable '{{{{ {v} }}}}' is not in the provided variable set")

    if title_template:
        unk, _ = validate_variables(title_template, allowed_set)
        for v in unk:
            warnings.append(f"Variable '{{{{ {v} }}}}' in title template is not in the provided variable set")

    try:
        tmpl = _sandbox_env.from_string(body_template)
        rendered_body = tmpl.render(**variables)
        result.body = rendered_body
    except Exception as exc:
        errors.append(f"Body template rendering error: {exc}")
        result.body = body_template

    if title_template:
        try:
            tmpl = _sandbox_env.from_string(title_template)
            rendered_title = tmpl.render(**variables)
            result.title = rendered_title
        except Exception as exc:
            errors.append(f"Title template rendering error: {exc}")
            result.title = title_template

    result.warnings = warnings
    result.errors = errors
    return result


# ─── Platform-specific renderers ────────────────────────────────────


def _get_limits(platform: ProviderEnum) -> dict[str, int]:
    return PLATFORM_LIMITS.get(platform.value, PLATFORM_LIMITS["mock"])


def calculate_length(content: str, platform: ProviderEnum) -> tuple[int, int | None, bool]:
    limits = _get_limits(platform)
    if platform == ProviderEnum.instagram:
        max_len = limits["caption_max_length"]
    elif platform == ProviderEnum.x:
        max_len = limits["post_max_length"]
    else:
        max_len = limits["post_max_length"]
    length = len(content)
    return length, max_len, length > max_len


def render_for_platform(
    body_template: str,
    variables: dict[str, Any],
    platform: ProviderEnum,
    title_template: str | None = None,
    campaign_tag: str | None = None,
) -> RenderResult:
    result = render_template(
        body_template=body_template,
        variables=variables,
        title_template=title_template,
    )

    if result.errors:
        return result

    limits = _get_limits(platform)

    if platform == ProviderEnum.instagram:
        result = _postprocess_instagram(result, limits, campaign_tag)
    elif platform == ProviderEnum.x:
        result = _postprocess_x(result, limits, campaign_tag)

    return result


def _postprocess_instagram(
    result: RenderResult,
    limits: dict[str, int],
    campaign_tag: str | None = None,
) -> RenderResult:
    body = result.body

    if len(body) > limits["caption_max_length"]:
        result.warnings.append(
            f"Caption exceeds Instagram limit of {limits['caption_max_length']} characters "
            f"(currently {len(body)})"
        )

    hashtags = re.findall(r"#\w+", body)
    if len(hashtags) > limits["hashtag_max_count"]:
        result.warnings.append(
            f"Too many hashtags ({len(hashtags)}); Instagram allows max {limits['hashtag_max_count']}"
        )

    strip_trailing_newlines = True
    stripped = body.rstrip("\n")
    if len(stripped) != len(body):
        body = stripped

    result.body = body
    return result


def _postprocess_x(
    result: RenderResult,
    limits: dict[str, int],
    campaign_tag: str | None = None,
) -> RenderResult:
    body = result.body

    if len(body) > limits["post_max_length"]:
        result.warnings.append(
            f"Post exceeds X/Twitter limit of {limits['post_max_length']} characters "
            f"(currently {len(body)})"
        )

    strip_trailing_newlines = True
    stripped = body.rstrip("\n")
    if len(stripped) != len(body):
        body = stripped

    result.body = body
    return result


# ─── UTM generator ──────────────────────────────────────────────────


def generate_utm_url(
    base_url: str,
    campaign_tag: str | None = None,
    source: str = "social",
    medium: str = "social",
    content: str | None = None,
) -> str:
    params = []
    params.append(("utm_source", source))
    params.append(("utm_medium", medium))
    if campaign_tag:
        params.append(("utm_campaign", campaign_tag))
    if content:
        params.append(("utm_content", content))

    import urllib.parse

    query_string = urllib.parse.urlencode(params)
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{query_string}"
