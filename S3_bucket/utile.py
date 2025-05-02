from sqlalchemy.orm import Session
from datetime import datetime
from auth.models import SEOFile, PPCFile
from auth.auth import get_db
from fastapi import Request, HTTPException, Depends
from typing import Union

def convert_into_csvdata(json_data):

    flattened_data = []

    for item in json_data:
        # if "Pages" not in item or not item["Pages"]:
        #     continue
        
        # for page in item["Pages"]:
        #     if not isinstance(page, dict):
        #         continue

        page_title = item.get("Page_Title", "")
        intent = item.get("Intent", "")
        url = item.get("Suggested_URL_Structure", "")

        if "Keywords" not in item or not isinstance(item["Keywords"], list):
            continue

        for keyword in item["Keywords"]:
            if not isinstance(keyword, dict) or "Keyword" not in keyword or "Avg_Monthly_Searches" not in keyword:
                continue
            
            keyword_text = keyword["Keyword"]
            avg_monthly_searches = keyword["Avg_Monthly_Searches"]  # Extracted from the input data
            
            flattened_data.append({
                "page_title": page_title,
                "keyword": keyword_text,
                "intent": intent,
                "url_structure": url,
                "avg_monthly_searches": avg_monthly_searches  # Added the search volume from the input
            })

    return flattened_data



def upload_seo_table( uuid: str, user_id: int, file_name: str, json_data: Union[dict, list]):
    db = next(get_db()) 
    try:
        new_file = SEOFile(
            user_id=user_id,
            file_name=file_name,
            uuid=uuid,
            json_data= json_data,
            upload_time=datetime.utcnow()
        )

        
        db.add(new_file)
        db.commit()
        db.refresh(new_file)

        return new_file  # You can return the created object if needed

    except Exception as e:
        db.rollback()
        raise Exception(f"Error storing SEO file in table: {str(e)}")
    finally:
        db.close() 
    
def upload_ppc_table( uuid: str, user_id: int, file_name: str, json_data: Union[dict, list]):
    db = next(get_db()) 
    try:
        new_file = PPCFile(
            user_id=user_id,
            file_name=file_name,
            uuid=uuid,
            json_data= json_data,
            upload_time=datetime.utcnow()
        )

        
        db.add(new_file)
        db.commit()
        db.refresh(new_file)

        return new_file  # You can return the created object if needed

    except Exception as e:
        db.rollback()
        raise Exception(f"Error storing SEO file in table: {str(e)}")
    finally:
        db.close() 
    