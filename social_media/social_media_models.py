from pydantic import BaseModel
from typing import Optional
from typing import Optional, List, Dict

class DocumentData(BaseModel):
    data: Dict[str, str]          

class CsvData(BaseModel):
    data: Dict[str, str] 


