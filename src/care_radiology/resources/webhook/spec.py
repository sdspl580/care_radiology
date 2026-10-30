import re

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from care_radiology.utils.accession import ACCESSION_NUMBER_LENGTH

MPPS_STATUS_MAX_LENGTH = 32
MPPS_STATUS_COMPLETED = "completed"


class MppsWebhookSpec(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
        alias_generator=to_camel,
        validate_by_name=True,
    )

    accession_number: str = Field(
        min_length=ACCESSION_NUMBER_LENGTH, max_length=ACCESSION_NUMBER_LENGTH
    )
    status: str
    procedure_step_id: str | None = Field(default=None, max_length=64)
    mpps_sop_instance_uid: str | None = Field(
        default=None, max_length=64, pattern=r"^[0-9.]+$"
    )

    @field_validator("accession_number")
    @classmethod
    def validate_accession_number(cls, value: str) -> str:
        value = value.lower()
        if any(c not in "0123456789abcdef" for c in value):
            raise ValueError("accessionNumber must be 16 hex characters")
        return value

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        # "IN PROGRESS" / "In_Progress" / "in-progress" -> "inprogress"
        value = re.sub(r"[^a-z0-9]", "", value.lower())
        if not value:
            raise ValueError("status must contain letters or digits")
        if len(value) > MPPS_STATUS_MAX_LENGTH:
            raise ValueError(f"status must be at most {MPPS_STATUS_MAX_LENGTH} characters")
        return value
