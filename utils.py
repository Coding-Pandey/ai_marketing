import json

def flatten_seo_data(json_data):
    """
    Flattens the nested SEO JSON data into a structured format.

    Args:
        json_data (list): List of dictionaries containing page titles, keywords, intent, and URLs.

    Returns:
        list: A list of dictionaries with page title, keyword, intent, and URL.
    """
    flattened_data = []

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
                    "url_structure": url
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