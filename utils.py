import json
import pandas as pd
from typing import List, Optional

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