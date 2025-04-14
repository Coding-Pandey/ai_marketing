from pydantic import BaseModel
from typing import Optional
from typing import Optional, List, Dict


class KeywordRequest(BaseModel):
    keywords: Optional[str] = None
    description: Optional[str] = None
    exclude_values: Optional[List[int]] = []
    branded_keyword: Optional[List[str]] = []
    location_ids: Optional[List[int]] = None
    language_id: Optional[int] = None
    branded_words: Optional[bool] = None

    def validate(self):
        if not self.keywords and not self.description:
            raise ValueError("At least one of 'keywords' or 'description' must be provided")
        if self.location_ids is None or self.language_id is None:
            raise ValueError("Both 'location_ids' and 'language_id' must be provided")

class SuggestionKeywordRequest(BaseModel):
    keywords: Optional[str] = None
    description: Optional[str] = None

    def validate(self):
        if not self.keywords and not self.description:
            raise ValueError("At least one of 'keywords' or 'description' must be provided") 

# Pydantic model to validate incoming dictionary
class DocumentData(BaseModel):
    data: Dict[str, str]          

class CsvData(BaseModel):
    data: Dict[str, str] 