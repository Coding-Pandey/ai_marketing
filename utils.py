from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from auth.models import UserPermission, FileStorage, SEOCSV, PPCCSV, SEOKeywords, PPCKeywords, SEOCluster,Contentgeneration, PPCCluster, SocialMedia
from auth.auth import get_current_user 
from auth.auth import get_db
import json
import pandas as pd
from typing import List, Optional
import os
import spacy
from dotenv import load_dotenv
load_dotenv()
from collections import defaultdict
import json
import pandas as pd
# Load the large English model
nlp = spacy.load("en_core_web_sm")

from jose import JWTError, jwt
from typing import Optional
from datetime import datetime, timedelta

BRANDED_JSON_PATH = os.environ.get("BRANDED_JSON_PATH")

SECRET_KEY = os.environ.get("JWT_SECRET")
ALGORITHM = os.environ.get("JWT_ALGORITHM")
print(f"Path: {BRANDED_JSON_PATH}")
# print(BRANDED_JSON_PATH)
def remove_keywords(data):
    """Removes entries from data where Keyword (case-insensitive) matches any in keywords_to_remove."""
    
    with open(BRANDED_JSON_PATH, "r", encoding="utf-8") as f:
        keywords_to_remove = json.load(f)

    # Extract keywords to exclude (lowercased for case-insensitive matching)
    keywords_to_exclude = {item["Keywords"].lower() for item in keywords_to_remove}

    # Remove matching keywords but retain the original casing
    filtered_data = [item for item in data if item.Keyword.lower() not in keywords_to_exclude]

    return filtered_data

def add_keywords_to_json(new_keywords):
    try:
   
        with open(BRANDED_JSON_PATH, 'r', encoding='utf-8') as f:
            csv_json_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        csv_json_data = [] 
    
    existing_keywords = {item['Keywords'].strip().lower() for item in csv_json_data}

    
    added = False
    for keyword in new_keywords:
        keyword_clean = keyword.strip()
        if keyword_clean.lower() not in existing_keywords:
            csv_json_data.append({"Keywords": keyword_clean})
            existing_keywords.add(keyword_clean.lower())
            print(f"Added '{keyword_clean}' to {BRANDED_JSON_PATH}")
            added = True
        else:
            print(f"Keyword '{keyword_clean}' already exists in {BRANDED_JSON_PATH}")

    
    if added:
        with open(BRANDED_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(csv_json_data, f, indent=4, ensure_ascii=False)
            
def filter_non_branded_keywords(keyword_list):
    """Removes keywords that are recognized as brands (ORG or PRODUCT) by spaCy."""
    return [
        item for item in keyword_list
        if not any(ent.label_ in ["ORG", "PRODUCT"] for ent in nlp(item.Keyword).ents)
    ]

def flatten_seo_data(json_data, search_volume_df):
    flattened_data = []

    # Create a mapping dictionary for fast lookup
    keyword_search_volume = dict(zip(search_volume_df["Keyword"], search_volume_df["Avg_Monthly_Searches"]))

    for item in json_data:  
        if "Pages" not in item or not item["Pages"]:  
            continue
        
        for page in item["Pages"]:  
            if not isinstance(page, dict):  
                continue

            page_title = page.get("Page Title", "")  
            intent = page.get("Intent", "")
            url = page.get("Suggested URL Structure", "")

            if "Keywords" not in page or not isinstance(page["Keywords"], list):
                continue  

            for keyword in page["Keywords"]:
                flattened_data.append({
                    "page_title": page_title,
                    "keyword": keyword,
                    "intent": intent,
                    "url_structure": url,
                    "avg_monthly_searches": keyword_search_volume.get(keyword, 0)  # Map search volume
                })

    return flattened_data

def map_seo_pages_with_search_volume(json_data, search_volume_df):
    processed_data = []

    # Create a mapping dictionary for fast lookup (case-insensitive)
    keyword_search_volume = {k.lower(): v for k, v in 
                              zip(search_volume_df["Keyword"], 
                                  search_volume_df["Avg_Monthly_Searches"])}

    # Handle different input formats
    pages_to_process = []
    if isinstance(json_data, list):
        # If json_data is already a list of pages
        if all(isinstance(item, dict) and "Page Title" in item for item in json_data):
            pages_to_process = json_data
        # If json_data contains items with "Pages" key
        else:
            for item in json_data:
                if isinstance(item, dict) and "Pages" in item and isinstance(item["Pages"], list):
                    pages_to_process.extend(item["Pages"])

    page_id_counter = 1  # Start page_title_id from 1

    for page in pages_to_process:
        if not isinstance(page, dict):
            continue

        page_title = page.get("Page Title", "")
        intent = page.get("Intent", "")
        url = page.get("Suggested URL Structure", "")
        
        # Process keywords and add search volumes
        keywords_with_volume = []
        keywords_data = page.get("Keywords", [])
        
        keyword_index = 1  # reset keyword index for each page
        
        # Handle different input formats for keywords
        if isinstance(keywords_data, list):
            if all(isinstance(k, str) for k in keywords_data if k):
                for keyword in keywords_data:
                    if keyword:
                        volume = keyword_search_volume.get(keyword.lower(), 0)
                        keywords_with_volume.append({
                            "Keyword_id": f"{page_id_counter}.{keyword_index}",
                            "Keyword": keyword,
                            "Avg_Monthly_Searches": volume
                        })
                        keyword_index += 1

            elif all(isinstance(k, dict) and "Keyword" in k for k in keywords_data if k):
                for keyword_obj in keywords_data:
                    if keyword_obj and "Keyword" in keyword_obj:
                        keyword = keyword_obj["Keyword"]
                        if "Avg_Monthly_Searches" in keyword_obj:
                            volume = keyword_obj["Avg_Monthly_Searches"]
                        else:
                            volume = keyword_search_volume.get(keyword.lower(), 0)
                        
                        keywords_with_volume.append({
                            "Keyword_id": f"{page_id_counter}.{keyword_index}",
                            "Keyword": keyword,
                            "Avg_Monthly_Searches": volume
                        })
                        keyword_index += 1

        elif isinstance(keywords_data, dict):
            for keyword, volume in keywords_data.items():
                keywords_with_volume.append({
                    "Keyword_id": f"{page_id_counter}.{keyword_index}",
                    "Keyword": keyword,
                    "Avg_Monthly_Searches": volume
                })
                keyword_index += 1

        # Create the new page structure
        processed_page = {
            "Page_title_id": str(page_id_counter),
            "Page_Title": page_title,
            "Keywords": keywords_with_volume,
            "Intent": intent,
            "Suggested_URL_Structure": url
        }

        processed_data.append(processed_page)
        page_id_counter += 1  # Increase page ID for next page

    return processed_data



def extract_first_json_object(text):
    """
    Extracts the first complete JSON object from `{` to `}` found in the input text.

    Args:
        text (str): The input text containing JSON data.

    Returns:
        dict: The extracted JSON object as a dictionary, or None if no valid JSON is found.
    """
    brace_count = 0
    json_str = ""
    start_index = None

    for i, char in enumerate(text):
        if char == "{":
            if brace_count == 0:
                start_index = i  # Mark the beginning of the JSON object
            brace_count += 1
        elif char == "}":
            brace_count -= 1
        
        if brace_count > 0 or (brace_count == 0 and start_index is not None):
            json_str += char
        
        if brace_count == 0 and start_index is not None:
            break  # Stop when the first valid JSON object is found

    if json_str:
        try:
            return json.loads(json_str)  # Convert to dictionary
        except json.JSONDecodeError:
            return None  # Return None if JSON parsing fails

    return None  # Return None if no valid JSON object is found

def filter_keywords_by_searches(keyword_ideas, exclude_values: List[int]):
    """
    Removes keyword dictionaries where avg_monthly_searches matches any value in exclude_values.
    """
    return [
        idea for idea in keyword_ideas
        if idea["Avg_Monthly_Searches"] not in exclude_values
    ]


def flatten_ppc_data(json_data, df):
    processed_data = []

    # Create a mapping dictionary for fast lookup (case-insensitive)
    keyword_search_volume = {k.lower(): v for k, v in 
                             zip(df["Keyword"], 
                                 df["Avg_Monthly_Searches"])}

    # Handle different input formats
    pages_to_process = []
    if isinstance(json_data, list):
        # Process all items in the list
        for item in json_data:
            if isinstance(item, dict):
                # If item has "Pages" key
                if "Pages" in item and isinstance(item["Pages"], list):
                    pages_to_process.extend(item["Pages"])
                # If item is already a page
                elif "Ad Group" in item or "Ad_Group" in item:
                    pages_to_process.append(item)

    page_id_counter = 1  # Start page_title_id from 1

    for page in pages_to_process:
        if not isinstance(page, dict):
            continue

        # Extract page data with corrected keys (handle both formats)
        ad_group = page.get("Ad Group", page.get("Ad_Group", ""))
        
        # Handle both "Ad Headline" and "Ad_Headlines" keys
        ad_headlines = []
        if "Ad Headline" in page and isinstance(page["Ad Headline"], list):
            ad_headlines = page["Ad Headline"]
        elif "Ad Headlines" in page and isinstance(page["Ad Headlines"], list):
            ad_headlines = page["Ad Headlines"]
        elif "Ad_Headlines" in page and isinstance(page["Ad_Headlines"], list):
            ad_headlines = page["Ad_Headlines"]
            
        # Handle both "Description" and "Descriptions" keys
        descriptions = []
        if "Description" in page and isinstance(page["Description"], list):
            descriptions = page["Description"]
        elif "Descriptions" in page and isinstance(page["Descriptions"], list):
            descriptions = page["Descriptions"]
        
        # Process keywords and add search volumes
        keywords_with_volume = []
        keywords_data = page.get("Keywords", [])
        
        keyword_index = 1  # Reset keyword index for each page
        
        # Handle different input formats for keywords
        if isinstance(keywords_data, list):
            if all(isinstance(k, str) for k in keywords_data if k):
                for keyword in keywords_data:
                    if keyword:
                        volume = keyword_search_volume.get(keyword.lower(), 0)
                        keywords_with_volume.append({
                            "Keyword_id": f"{page_id_counter}.{keyword_index}",
                            "Keyword": keyword,
                            "Avg_Monthly_Searches": volume
                        })
                        keyword_index += 1
            elif all(isinstance(k, dict) and "Keyword" in k for k in keywords_data if k):
                for keyword_obj in keywords_data:
                    if keyword_obj and "Keyword" in keyword_obj:
                        keyword = keyword_obj["Keyword"]
                        if "Avg_Monthly_Searches" in keyword_obj:
                            volume = keyword_obj["Avg_Monthly_Searches"]
                        else:
                            volume = keyword_search_volume.get(keyword.lower(), 0)
                        keywords_with_volume.append({
                            "Keyword_id": f"{page_id_counter}.{keyword_index}",
                            "Keyword": keyword,
                            "Avg_Monthly_Searches": volume
                        })
                        keyword_index += 1
        elif isinstance(keywords_data, dict):
            for keyword, volume in keywords_data.items():
                keywords_with_volume.append({
                    "Keyword_id": f"{page_id_counter}.{keyword_index}",
                    "Keyword": keyword,
                    "Avg_Monthly_Searches": volume
                })
                keyword_index += 1

        # Transform Ad_Headlines into a list of dictionaries with IDs
        headline_list = [
            {"Headlines_id": f"{page_id_counter}.{i+1}", "Ad_Headline": headline}
            for i, headline in enumerate(ad_headlines)
        ]

        # Transform Descriptions into a list of dictionaries with IDs
        description_list = [
            {"Description_id": f"{page_id_counter}.{i+1}", "Description": description}
            for i, description in enumerate(descriptions)
        ]

        # Create the new page structure
        processed_page = {
            "Page_title_id": str(page_id_counter),
            "Ad_Group": ad_group,
            "Keywords": keywords_with_volume,
            "Ad_Headlines": headline_list,
            "Descriptions": description_list
        }

        processed_data.append(processed_page)
        page_id_counter += 1  # Increase page ID for next page

    return processed_data



def remove_branded_keywords(keywords_list, branded_keywords_list):
    # Create a new list to store filtered keywords
    filtered_keywords = []
    
    # Convert branded keywords to lowercase for case-insensitive comparison
    branded_keywords_lower = [brand.lower() for brand in branded_keywords_list]
    
    # Filter out branded keywords
    for keyword_item in keywords_list:
        keyword_lower = keyword_item.Keyword.lower()
        
        # Check if the keyword contains any branded keyword
        is_branded = any(brand in keyword_lower for brand in branded_keywords_lower)
        
        # If not branded, add to filtered list
        if not is_branded:
            filtered_keywords.append(keyword_item)
    
    return filtered_keywords

def filter_by_branded(
    keywords_list,
    branded_keywords_list,
    include: bool = False
):
    """
    If include=True, returns only keywords that contain any branded term.
    If include=False, returns only keywords that do NOT contain any branded term.
    """
    result = []
    branded_lower = [b.lower() for b in branded_keywords_list]

    for item in keywords_list:
        has_brand = any(brand in item.Keyword.lower() for brand in branded_lower)
        if (include and has_brand) or (not include and not has_brand):
            result.append(item)

    return result



def extract_keywords(json_string):
    """Validate JSON and extract 'keywords' list if present.
    Returns keywords list if valid and <= 20 keywords with duplicates removed,
    or a tuple (False, error_message) otherwise.
    """
    try:
        if isinstance(json_string, dict): 
            parsed_json = json_string
        else:
            parsed_json = json.loads(json_string)  

        if "keywords" in parsed_json and isinstance(parsed_json["keywords"], list):
            unique_keywords = []
            for keyword in parsed_json["keywords"]:
                if keyword not in unique_keywords:
                    unique_keywords.append(keyword)
            

            if len(unique_keywords) > 20:
                return False, "Please enter only 20 keywords."
                
            return unique_keywords  
        else:
            return False, "'keywords' field is missing or not a list."
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}" 
    



def group_by_page_title(data):
    grouped_data = defaultdict(lambda: {"keywords": [], "monthly_search_volume": [], "intent": [], "urls": []})
    
    for entry in data:
        page_title = entry["page_title"]
        grouped_entry = grouped_data[page_title]
        
        # Append values ensuring uniqueness
        if entry["keyword"] not in grouped_entry["keywords"]:
            grouped_entry["keywords"].append(entry["keyword"])
        
        if entry["monthly_search_volume"] not in grouped_entry["monthly_search_volume"]:
            grouped_entry["monthly_search_volume"].append(entry["monthly_search_volume"])
        
        if entry["intent"] not in grouped_entry["intent"]:
            grouped_entry["intent"].append(entry["intent"])
        
        if entry["url_structure"] not in grouped_entry["urls"]:
            grouped_entry["urls"].append(entry["url_structure"])
    
    # Convert defaultdict back to list of dicts
    return [{"page_title": title, **values} for title, values in grouped_data.items()]

#li = ["seo"]   
#add_keywords_to_json(li)
def verify_jwt_token(request: Request) -> str:
    auth_header: Optional[str] = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing authorization token")
    
    token = auth_header[len("Bearer "):]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        id: int = payload.get("id")

        if username is None or id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return username, id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")



def enforce_user_api_limit(user, db):
    if user.role in ["admin", "prime"]:
        return  # No limit for premium roles

    now = datetime.utcnow()
    # Reset if it's been more than 30 days
    if not user.last_reset or (now - user.last_reset) > timedelta(days=30):
        user.api_call_count = 0
        user.last_reset = now

    if user.api_call_count >= 10:
        raise HTTPException(status_code=429, detail="Monthly API limit reached")

    user.api_call_count += 1
    db.commit()




def check_api_limit(api_name: str):
    def _inner(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):

        if user.role == "admin":
            return user  # Admin bypasses the API limits

        # Check the corresponding table based on the `api_name`
        if api_name == "ppc_cluster":
            permission = db.query(PPCCluster).filter_by(user_id=user.id).first()
        elif api_name == "social_media":
            permission = db.query(SocialMedia).filter_by(user_id=user.id).first()         
        elif api_name == "seo_cluster":
            permission = db.query(SEOCluster).filter_by(user_id=user.id).first()
        elif api_name == "seo_csv":
            permission = db.query(SEOCSV).filter_by(user_id=user.id).first()         
        elif api_name == "ppc_csv":
            permission = db.query(PPCCSV).filter_by(user_id=user.id).first()
        elif api_name == "seo_keywords":
            permission = db.query(SEOKeywords).filter_by(user_id=user.id).first()        
        elif api_name == "ppc_keywords":
            permission = db.query(PPCKeywords).filter_by(user_id=user.id).first()
        elif api_name == "seo_cluster":
            permission = db.query(SEOCluster).filter_by(user_id=user.id).first()
        elif api_name == "ppc_cluster":
            permission = db.query(PPCCluster).filter_by(user_id=user.id).first()
        elif api_name == "social_media":
            permission = db.query(SocialMedia).filter_by(user_id=user.id).first()   
        # elif api_name == "social_media_file":
        #     permission = db.query().filter_by(user_id= user.id).first()    
        # 
        elif api_name == "content_generation":
            permission = db.query(Contentgeneration).filter_by(user_id=user.id).first()  
        # Add more checks for other APIs here as needed
        
        else:
            raise HTTPException(status_code=403, detail="No permission for this API")

        if not permission:
            raise HTTPException(status_code=403, detail="No permission for this API")

        # Reset monthly usage if needed
        now = datetime.utcnow()
        if permission.last_reset.month != now.month or permission.last_reset.year != now.year:
            permission.call_count = 0
            permission.last_reset = now

        if permission.call_count >= permission.call_limit:
            raise HTTPException(status_code=429, detail="API call limit exceeded")

        # Increment usage
        permission.call_count += 1
        db.commit()

        return user  # returns user so you can use it in the route
    return _inner


# def file_api_limit(api_name: str):
#     def _inner(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):

#         if user.role == "admin":
#             return user  # Admin bypasses the API limits
           
#         if api_name == "social_media_file":
#             permission = db.query().filter_by(user_id= user.id).first()      
#         # Add more checks for other APIs here as needed
        
#         else:
#             raise HTTPException(status_code=403, detail="No permission for this API")

#         if not permission:
#             raise HTTPException(status_code=403, detail="No permission for this API")

#         # Reset monthly usage if needed
#         now = datetime.utcnow()
#         if permission.last_reset.month != now.month 
#             permission.call_count = 0
#             permission.last_reset = now

#         if permission.call_count >= permission.call_limit:
#             raise HTTPException(status_code=429, detail="API call limit exceeded")

#         # Increment usage
#         permission.call_count += 1
#         db.commit()

#         return user  # returns user so you can use it in the route
#     return _inner