import json
import pandas as pd
from typing import List, Optional
import os
import spacy
from dotenv import load_dotenv
load_dotenv()
# Load the large English model
nlp = spacy.load("en_core_web_sm")

BRANDED_JSON_PATH = os.environ.get("BRANDED_JSON_PATH")
print(f"Path: {BRANDED_JSON_PATH}")
# print(BRANDED_JSON_PATH)
def remove_keywords(data):
    """Removes entries from data where Keyword (case-insensitive) matches any in keywords_to_remove."""
    
    with open(BRANDED_JSON_PATH, "r", encoding="utf-8") as f:
        keywords_to_remove = json.load(f)

    # Extract keywords to exclude (lowercased for case-insensitive matching)
    keywords_to_exclude = {item["Keywords"].lower() for item in keywords_to_remove}

    # Remove matching keywords but retain the original casing
    filtered_data = [item for item in data if item["Keyword"].lower() not in keywords_to_exclude]

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
        if not any(ent.label_ in ["ORG", "PRODUCT"] for ent in nlp(item["Keyword"]).ents)
    ]

def flatten_seo_data(json_data, search_volume_df):
    flattened_data = []

    # Create a mapping dictionary for fast lookup
    keyword_search_volume = dict(zip(search_volume_df["Keyword"], search_volume_df["Avg Monthly Searches"]))

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
        if idea["Avg Monthly Searches"] not in exclude_values
    ]


def flatten_ppc_data(json_data, df):

    # ✅ Convert DataFrame columns to dictionaries for quick lookup
    search_volume_map = df.set_index("Keyword")["Avg Monthly Searches"].to_dict()
    bid_low_map = df.set_index("Keyword")["LowTopOfPageBid"].to_dict()
    bid_high_map = df.set_index("Keyword")["HighTopOfPageBid"].to_dict()
    # currency_map = df.set_index("Keyword")["Currency"].to_dict()

    flattened_data = []

    for item in json_data:
        for page in item.get("Pages", []):
            ad_group = page.get("Ad Group", "")
            keywords = page.get("Keywords", [])
            ad_headlines = page.get("Ad Headline", [])
            descriptions = page.get("Description", [])

            # ✅ Get max length among lists to ensure complete iteration
            max_len = max(len(keywords), len(ad_headlines), len(descriptions))

            for i in range(max_len):
                keyword = keywords[i] if i < len(keywords) else None

                record = {
                    "Ad Group": ad_group,
                    "Keywords": keyword,
                    "Avg. Monthly Searches": search_volume_map.get(keyword, None) if keyword else None,
                    "Top of Page Bid Low": bid_low_map.get(keyword, None) if keyword else None,
                    "Top of Page Bid High": bid_high_map.get(keyword, None) if keyword else None,
                    "Ad Headline": ad_headlines[i] if i < len(ad_headlines) else None,
                    "Description": descriptions[i] if i < len(descriptions) else None,
                    # "Currency": currency_map.get(keyword, None) if keyword else None,
                }
                flattened_data.append(record)

    return flattened_data


def remove_branded_keywords(keywords_list, branded_keywords_list):
    # Create a new list to store filtered keywords
    filtered_keywords = []
    
    # Convert branded keywords to lowercase for case-insensitive comparison
    branded_keywords_lower = [brand.lower() for brand in branded_keywords_list]
    
    # Filter out branded keywords
    for keyword_item in keywords_list:
        keyword_lower = keyword_item['Keyword'].lower()
        
        # Check if the keyword contains any branded keyword
        is_branded = any(brand in keyword_lower for brand in branded_keywords_lower)
        
        # If not branded, add to filtered list
        if not is_branded:
            filtered_keywords.append(keyword_item)
    
    return filtered_keywords



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
    

from collections import defaultdict
import json
import pandas as pd

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
