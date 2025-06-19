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

class KeywordItem(BaseModel):
    Keyword: str
    Avg_Monthly_Searches: int    

class UUIDRequest(BaseModel):
    uuid: str
    def validate(self):
        if not self.uuid:
            raise ValueError("UUID must be provided")
        
# Pydantic models for update requests
class KeywordUpdate(BaseModel):
    Keyword: Optional[str]
    # Avg_Monthly_Searches: Optional[int]

class PageUpdate(BaseModel):
    Page_Title: Optional[str]
    Suggested_URL_Structure: Optional[str]        


class RemoveKeyword(BaseModel):
    branded_words: Optional[bool] = False
    branded_keyword: Optional[List[str]] = []

class KeywordClusterRequest(BaseModel):
    keywords: List[KeywordItem]
    delete_word: Optional[RemoveKeyword] = None    


class SiteData(BaseModel):
    site_url: str
    search_type: str = "web"  # e.g., "web", "image", "video"
    country: Optional[str] = None  # ISO 3166-1 alpha-3 code, e.g., "USA"
    device_type: Optional[str] = None  # e.g., "mobile", "desktop", "tablet"
    start_date: str  # YYYY-MM-DD
    end_date: str       


class SEOFileNameUpdate(BaseModel):
    file_name: str    