"""Prompt injection defense: sanitize tool outputs before feeding to LLM context."""

from __future__ import annotations

import re

# Patterns that look like injected instructions
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a\s+)?(?:new\s+)?(?:different\s+)?(?:AI|assistant|bot|GPT|Claude)", re.IGNORECASE),
    re.compile(r"forget\s+(?:everything|all|prior)(?:\s+previous)?\s+(?:instructions?|context|directives?)", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
    # "SYSTEM:" at start of string or on its own line (role injection)
    re.compile(r"(?:^|\n)\s*SYSTEM\s*:", re.IGNORECASE),
    re.compile(r"<\s*/?(?:system|instruction|prompt)\s*>", re.IGNORECASE),
    re.compile(r"\[INST\]|\[/INST\]|\[SYS\]|\[/SYS\]", re.IGNORECASE),
    re.compile(r"###\s*(?:System|Instruction|Override)", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions?|messages?|rules?)", re.IGNORECASE),
    re.compile(r"(?:new|updated)\s+instructions?:", re.IGNORECASE),
    re.compile(r"act\s+as\s+(?:if\s+you\s+(?:are|were)|a\s+)", re.IGNORECASE),
    re.compile(r"do\s+not\s+(?:follow|obey|adhere\s+to)", re.IGNORECASE),
    re.compile(r"override\s+(?:your\s+)?(?:system|safety|previous)", re.IGNORECASE),
]

_MAX_CONTENT_LENGTH = 8000  # characters; trim before injection


def sanitize_tool_output(content: str) -> str:
    """Remove prompt-injection patterns from tool output before passing to LLM."""
    if not content:
        return content

    sanitized = content[:_MAX_CONTENT_LENGTH]

    for pattern in _INJECTION_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)

    return sanitized


def sanitize_search_results(results: list[dict]) -> list[dict]:
    """Sanitize a list of search result dicts (title, snippet, url)."""
    cleaned = []
    for result in results:
        cleaned.append(
            {
                **result,
                "title": sanitize_tool_output(result.get("title", "")),
                "snippet": sanitize_tool_output(result.get("snippet", "")),
            }
        )
    return cleaned
