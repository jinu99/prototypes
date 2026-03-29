"""1-pass and 2-pass extraction pipelines."""

from .models import (
    EXTRACTION_MODELS,
    FieldEvidence,
    VerificationReport,
)
from .mock_llm import mock_extract, mock_verify_field


HALLUCINATION_THRESHOLD = 0.5


def run_one_pass(text: str, schema_type: str) -> dict:
    """1-pass: extract structured data from text, no verification."""
    model_cls = EXTRACTION_MODELS.get(schema_type)
    if not model_cls:
        raise ValueError(f"Unknown schema: {schema_type}")

    raw = mock_extract(text, schema_type)
    validated = model_cls.model_validate(raw)
    return validated.model_dump()


def run_two_pass(text: str, schema_type: str) -> VerificationReport:
    """2-pass: extract then verify each field against source text."""
    model_cls = EXTRACTION_MODELS.get(schema_type)
    if not model_cls:
        raise ValueError(f"Unknown schema: {schema_type}")

    # Pass 1: Extract
    raw = mock_extract(text, schema_type)
    validated = model_cls.model_validate(raw)
    extracted = validated.model_dump()

    # Pass 2: Verify each field
    evidences: list[FieldEvidence] = []

    for field_name, value in extracted.items():
        if isinstance(value, list):
            # Verify each list item individually
            for i, item in enumerate(value):
                item_str = str(item)
                verification = mock_verify_field(text, field_name, item_str)
                is_hallucination = verification["confidence"] < HALLUCINATION_THRESHOLD
                evidences.append(FieldEvidence(
                    field_name=f"{field_name}[{i}]",
                    extracted_value=item_str,
                    evidence_span=verification["evidence_span"],
                    confidence=verification["confidence"],
                    is_hallucination=is_hallucination,
                    reasoning=verification["reasoning"],
                ))
        else:
            value_str = str(value) if value is not None else ""
            if not value_str or value_str == "None":
                continue

            verification = mock_verify_field(text, field_name, value_str)
            is_hallucination = verification["confidence"] < HALLUCINATION_THRESHOLD
            evidences.append(FieldEvidence(
                field_name=field_name,
                extracted_value=value_str,
                evidence_span=verification["evidence_span"],
                confidence=verification["confidence"],
                is_hallucination=is_hallucination,
                reasoning=verification["reasoning"],
            ))

    total = len(evidences)
    hallucinated = sum(1 for e in evidences if e.is_hallucination)
    verified = total - hallucinated

    return VerificationReport(
        source_text=text,
        model_name=schema_type,
        extracted_data=extracted,
        field_evidences=evidences,
        total_fields=total,
        verified_fields=verified,
        hallucination_candidates=hallucinated,
        hallucination_rate=hallucinated / total if total > 0 else 0.0,
    )


def compare_passes(text: str, schema_type: str) -> dict:
    """Compare 1-pass vs 2-pass, returning summary stats."""
    one_pass_result = run_one_pass(text, schema_type)
    two_pass_report = run_two_pass(text, schema_type)

    flagged_fields = [
        e.field_name for e in two_pass_report.field_evidences if e.is_hallucination
    ]

    return {
        "one_pass_result": one_pass_result,
        "two_pass_report": two_pass_report,
        "flagged_as_hallucination": flagged_fields,
        "hallucination_rate": two_pass_report.hallucination_rate,
    }
