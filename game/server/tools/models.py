from __future__ import annotations

from pydantic import BaseModel


class LayoutImportJs(BaseModel):
    #: Layouts available after the import.
    count: int


class PretenseCampaignJs(BaseModel):
    #: The generated .miz file.
    path: str
