"""Request and response bodies for Facility Management. Input is validated here, before any service.

The limits come from the facilities table (name is String(100)) and FR-02: a facility must have a
name and room for at least one person. Out-of-range input is rejected with 422 by FastAPI.
"""

from pydantic import BaseModel, ConfigDict, Field

NAME_MAX_LENGTH = 100


class FacilityCreate(BaseModel):
    """A new facility. requires_approval marks restricted facilities (FR-08)."""

    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    capacity: int = Field(ge=1)
    requires_approval: bool = False


class FacilityUpdate(BaseModel):
    """A partial update: only the fields that are sent (and not null) are changed."""

    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX_LENGTH)
    capacity: int | None = Field(default=None, ge=1)
    requires_approval: bool | None = None


class FacilityOut(BaseModel):
    """A facility as every authenticated user sees it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    capacity: int
    requires_approval: bool
    active: bool
