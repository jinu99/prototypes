"""Pydantic models for extraction targets and verification results."""

from pydantic import BaseModel, Field


# --- Extraction target models ---

class PersonProfile(BaseModel):
    """Person profile extracted from unstructured text."""
    name: str = Field(description="Full name of the person")
    age: int | None = Field(default=None, description="Age in years")
    occupation: str | None = Field(default=None, description="Current job title or occupation")
    company: str | None = Field(default=None, description="Company or organization")
    education: str | None = Field(default=None, description="Highest education or alma mater")
    location: str | None = Field(default=None, description="City or location")
    achievements: list[str] = Field(default_factory=list, description="Notable achievements")


class ProductInfo(BaseModel):
    """Product information extracted from a review or description."""
    product_name: str = Field(description="Name of the product")
    brand: str | None = Field(default=None, description="Brand or manufacturer")
    price: str | None = Field(default=None, description="Price mentioned")
    rating: str | None = Field(default=None, description="Rating or score")
    pros: list[str] = Field(default_factory=list, description="Positive aspects")
    cons: list[str] = Field(default_factory=list, description="Negative aspects")


class EventInfo(BaseModel):
    """Event information extracted from text."""
    event_name: str = Field(description="Name of the event")
    date: str | None = Field(default=None, description="Date of the event")
    location: str | None = Field(default=None, description="Venue or location")
    organizer: str | None = Field(default=None, description="Organizer or host")
    attendees: str | None = Field(default=None, description="Number of attendees or audience")
    description: str | None = Field(default=None, description="Brief description")


# --- Verification result models ---

class FieldEvidence(BaseModel):
    """Evidence mapping for a single extracted field."""
    field_name: str
    extracted_value: str
    evidence_span: str | None = Field(
        default=None,
        description="Substring from original text that supports this value"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score: 1.0=exact match, 0.0=no evidence"
    )
    is_hallucination: bool = Field(
        default=False,
        description="Flagged as likely hallucinated"
    )
    reasoning: str = Field(
        default="",
        description="Why this confidence was assigned"
    )


class VerificationReport(BaseModel):
    """Complete verification report for an extraction."""
    source_text: str
    model_name: str
    extracted_data: dict
    field_evidences: list[FieldEvidence]
    total_fields: int
    verified_fields: int
    hallucination_candidates: int
    hallucination_rate: float


EXTRACTION_MODELS = {
    "person": PersonProfile,
    "product": ProductInfo,
    "event": EventInfo,
}
