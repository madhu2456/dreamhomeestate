"""ListingMedia schemas."""

import uuid

from pydantic import BaseModel


class MediaReorderIn(BaseModel):
    order: dict[str, int]  # media_id -> new_order_index


class CoverUpdateOut(BaseModel):
    message: str
    media_id: uuid.UUID
