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
    Competition: str = None
    LowTopOfPageBid: Optional[float] = None
    HighTopOfPageBid: Optional[float] = None


from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel

class HeadlineUpdate(BaseModel):
    Headlines_id: Optional[str] = None
    Ad_Headline: str


class DescriptionUpdate(BaseModel):
    Description_id: Optional[str] = None
    Description: str



class ppcPageUpdate(BaseModel):
    Ad_Group: Optional[str] = None
    Ad_Headlines: Optional[List[Union[HeadlineUpdate, str]]] = None
    Descriptions: Optional[List[Union[DescriptionUpdate,str]]] = None


class UUIDRequest(BaseModel):
    uuid: str
    def validate(self):
        if not self.uuid:
            raise ValueError("UUID must be provided")
        

class RemoveKeyword(BaseModel):
    exclude: Optional[List[str]] = []
    include: Optional[List[str]] = []   

class KeywordClusterRequest(BaseModel):
    keywords: List[KeywordItem]
    delete_word: Optional[RemoveKeyword] = None    
    file_name: Optional[str] = None        


class PPCFileNameUpdate(BaseModel):
    file_name: Optional[str] = None
    def validate(self):
        if not self.file_name:
            raise ValueError("File name must be provided")    