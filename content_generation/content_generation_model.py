from pydantic import BaseModel
from typing import Optional
from typing import Optional, List, Dict

class UUIDRequest(BaseModel):
    uuid: str
    def validate(self):
        if not self.uuid:
            raise ValueError("UUID must be provided")