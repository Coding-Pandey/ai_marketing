from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class SheetDataOut(BaseModel):
    tab: str
    values: List[List[Optional[str]]]

    model_config = ConfigDict(from_attributes=True)