"""Structured output probe: JSON/YAML parsing success rate, schema compliance."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import yaml

from llm_qual_probe.client import LLMClient, LLMResponse


EXPECTED_SCHEMA = {
    "name": str,
    "age": int,
    "email": str,
}

JSON_PROMPTS = [
    'Return a JSON object with fields: name (string), age (integer), email (string). Only output valid JSON, no explanation.',
    'Generate a JSON object representing a person with name, age, and email fields. Output only the JSON.',
    'Create a JSON with keys "name" (string), "age" (number), "email" (string). No markdown, just raw JSON.',
    'Output a single JSON object: {"name": "...", "age": ..., "email": "..."}. Fill with realistic data.',
    'Respond with only a JSON object containing name, age, and email for a fictional person.',
]

YAML_PROMPTS = [
    'Return a YAML document with fields: name (string), age (integer), email (string). Only output valid YAML.',
    'Generate YAML representing a person with name, age, and email. No markdown fences.',
    'Create a YAML document with keys name, age, email. Output only the YAML content.',
]


@dataclass
class StructuredResult:
    format: str  # "json" or "yaml"
    prompt: str
    raw_output: str
    parse_success: bool
    schema_compliant: bool
    hallucinated_fields: list[str]
    missing_fields: list[str]
    type_errors: list[str]


def _extract_json(text: str) -> str:
    """Try to extract JSON from text that might have markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return text


def _check_schema(data: dict[str, Any]) -> tuple[bool, list[str], list[str], list[str]]:
    hallucinated = [k for k in data if k not in EXPECTED_SCHEMA]
    missing = [k for k in EXPECTED_SCHEMA if k not in data]
    type_errors = []
    for field, expected_type in EXPECTED_SCHEMA.items():
        if field in data and not isinstance(data[field], expected_type):
            type_errors.append(f"{field}: expected {expected_type.__name__}, got {type(data[field]).__name__}")
    compliant = not missing and not type_errors
    return compliant, hallucinated, missing, type_errors


def run_json_probe(client: LLMClient, count: int = 5) -> list[StructuredResult]:
    results = []
    for i in range(count):
        prompt = JSON_PROMPTS[i % len(JSON_PROMPTS)]
        resp = client.chat([
            {"role": "system", "content": "You are a helpful assistant that outputs structured data."},
            {"role": "user", "content": prompt},
        ], temperature=0.3)

        raw = resp.content
        extracted = _extract_json(raw)

        try:
            data = json.loads(extracted)
            parse_ok = True
        except (json.JSONDecodeError, ValueError):
            data = {}
            parse_ok = False

        if parse_ok and isinstance(data, dict):
            compliant, hallucinated, missing, type_errors = _check_schema(data)
        else:
            compliant, hallucinated, missing, type_errors = False, [], list(EXPECTED_SCHEMA.keys()), []

        results.append(StructuredResult(
            format="json",
            prompt=prompt,
            raw_output=raw,
            parse_success=parse_ok,
            schema_compliant=compliant,
            hallucinated_fields=hallucinated,
            missing_fields=missing,
            type_errors=type_errors,
        ))
    return results


def run_yaml_probe(client: LLMClient, count: int = 3) -> list[StructuredResult]:
    results = []
    for i in range(count):
        prompt = YAML_PROMPTS[i % len(YAML_PROMPTS)]
        resp = client.chat([
            {"role": "system", "content": "You are a helpful assistant that outputs structured data."},
            {"role": "user", "content": prompt},
        ], temperature=0.3)

        raw = resp.content
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        try:
            data = yaml.safe_load(text)
            parse_ok = isinstance(data, dict)
        except yaml.YAMLError:
            data = {}
            parse_ok = False

        if parse_ok and isinstance(data, dict):
            compliant, hallucinated, missing, type_errors = _check_schema(data)
        else:
            compliant, hallucinated, missing, type_errors = False, [], list(EXPECTED_SCHEMA.keys()), []

        results.append(StructuredResult(
            format="yaml",
            prompt=prompt,
            raw_output=raw,
            parse_success=parse_ok,
            schema_compliant=compliant,
            hallucinated_fields=hallucinated,
            missing_fields=missing,
            type_errors=type_errors,
        ))
    return results


def run(client: LLMClient) -> dict:
    json_results = run_json_probe(client)
    yaml_results = run_yaml_probe(client)
    all_results = json_results + yaml_results

    total = len(all_results)
    parse_ok = sum(1 for r in all_results if r.parse_success)
    schema_ok = sum(1 for r in all_results if r.schema_compliant)
    hallucination_count = sum(len(r.hallucinated_fields) for r in all_results)

    parse_rate = parse_ok / total if total else 0
    schema_rate = schema_ok / total if total else 0

    if parse_rate >= 0.8 and schema_rate >= 0.7:
        status = "PASS"
    elif parse_rate >= 0.5:
        status = "WARN"
    else:
        status = "FAIL"

    return {
        "probe": "structured_output",
        "status": status,
        "summary": {
            "total_tests": total,
            "parse_success": parse_ok,
            "parse_rate": round(parse_rate * 100, 1),
            "schema_compliant": schema_ok,
            "schema_rate": round(schema_rate * 100, 1),
            "hallucinated_fields_total": hallucination_count,
        },
        "details": [
            {
                "format": r.format,
                "prompt": r.prompt[:80],
                "parse_success": r.parse_success,
                "schema_compliant": r.schema_compliant,
                "hallucinated_fields": r.hallucinated_fields,
                "missing_fields": r.missing_fields,
                "type_errors": r.type_errors,
                "raw_output": r.raw_output[:200],
            }
            for r in all_results
        ],
    }
