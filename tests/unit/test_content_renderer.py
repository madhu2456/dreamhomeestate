"""Unit tests for content renderer service."""

import pytest

from app.models import ProviderEnum
from app.services.content_renderer import (
    ALLOWED_GLOBALS,
    PLATFORM_LIMITS,
    RenderResult,
    calculate_length,
    extract_variables,
    generate_utm_url,
    render_for_platform,
    render_template,
    validate_variables,
)


class TestExtractVariables:
    def test_extracts_simple_variable(self):
        result = extract_variables("{{ title }}")
        assert result == ["title"]

    def test_extracts_multiple_variables(self):
        result = extract_variables("{{ title }} - {{ price }} {{ currency }}")
        assert sorted(result) == ["currency", "price", "title"]

    def test_extracts_with_filters(self):
        result = extract_variables("{{ title|upper }} - {{ price|default('N/A') }}")
        assert sorted(result) == ["price", "title"]

    def test_returns_empty_list_for_no_variables(self):
        assert extract_variables("Hello world") == []

    def test_ignores_jinja_blocks(self):
        result = extract_variables("{% if title %}{{ title }}{% endif %}")
        assert result == ["title"]


class TestValidateVariables:
    def test_no_unknown_variables(self):
        unknown, missing = validate_variables("{{ title }}", {"title"})
        assert unknown == []
        assert missing == []

    def test_detects_unknown_variables(self):
        unknown, missing = validate_variables("{{ title }} {{ missing_var }}", {"title"})
        assert "missing_var" in unknown

    def test_detects_missing_variables(self):
        unknown, missing = validate_variables("{{ title }}", {"title", "price"})
        assert "price" in missing


class TestRenderTemplate:
    def test_renders_simple_template(self):
        result = render_template("Hello {{ name }}!", {"name": "World"})
        assert result.body == "Hello World!"
        assert result.errors == []

    def test_renders_title_template(self):
        result = render_template("Body {{ x }}", {"x": "test"}, title_template="Title {{ x }}")
        assert result.title == "Title test"
        assert result.body == "Body test"

    def test_warns_on_unknown_variables(self):
        result = render_template("{{ unknown }}", {"title": "hello"})
        assert "unknown" in result.warnings[0]

    def test_handles_render_error_gracefully(self):
        result = render_template("{{ invalid syntax }}", {})
        assert len(result.errors) > 0

    def test_allowed_globals_available(self):
        result = render_template("{{ max(1, 2, 3) }}", {})
        assert result.body == "3"

    def test_disallowed_imports_raise_error(self):
        result = render_template("{{ __import__('os').listdir() }}", {})
        assert len(result.errors) > 0

    def test_range_available(self):
        result = render_template("{% for i in range(3) %}{{ i }}{% endfor %}", {})
        assert result.body == "012"


class TestCalculateLength:
    def test_under_limit(self):
        length, max_len, exceeded = calculate_length("short", ProviderEnum.x)
        assert length == 5
        assert max_len == 280
        assert not exceeded

    def test_over_limit(self):
        long_text = "a" * 300
        length, max_len, exceeded = calculate_length(long_text, ProviderEnum.x)
        assert length == 300
        assert max_len == 280
        assert exceeded

    def test_instagram_limit(self):
        length, max_len, _ = calculate_length("test", ProviderEnum.instagram)
        assert max_len == 2200

    def test_mock_unlimited(self):
        length, max_len, exceeded = calculate_length("a" * 50000, ProviderEnum.mock)
        assert max_len == 10000
        assert exceeded


class TestRenderForPlatform:
    def test_instagram_strips_trailing_newlines(self):
        result = render_for_platform(
            body_template="Hello {{ name }}\n\n\n",
            variables={"name": "World"},
            platform=ProviderEnum.instagram,
        )
        assert result.body == "Hello World"

    def test_instagram_warns_on_long_caption(self):
        long = "a" * 2500
        result = render_for_platform(
            body_template="{{ text }}",
            variables={"text": long},
            platform=ProviderEnum.instagram,
        )
        assert any("caption exceeds" in w.lower() for w in result.warnings)

    def test_x_warns_on_long_post(self):
        long = "a" * 300
        result = render_for_platform(
            body_template="{{ text }}",
            variables={"text": long},
            platform=ProviderEnum.x,
        )
        assert any("x/twitter limit" in w.lower() for w in result.warnings)

    def test_errors_returned_for_bad_template(self):
        result = render_for_platform(
            body_template="{{ bad syntax }",
            variables={},
            platform=ProviderEnum.mock,
        )
        assert len(result.errors) > 0


class TestGenerateUtmUrl:
    def test_adds_utm_params(self):
        url = generate_utm_url(
            "https://example.com/listing/123",
            campaign_tag="summer2024",
            source="instagram",
            medium="social",
            content="beach-house",
        )
        assert "utm_source=instagram" in url
        assert "utm_medium=social" in url
        assert "utm_campaign=summer2024" in url
        assert "utm_content=beach-house" in url

    def test_handles_existing_query_params(self):
        url = generate_utm_url(
            "https://example.com/page?ref=home",
            source="x",
            medium="social",
        )
        assert "?ref=home&utm_source=x" in url or "&ref=home&utm_source=x" in url
