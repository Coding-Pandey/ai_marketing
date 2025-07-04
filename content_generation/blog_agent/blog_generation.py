import sys
import os
import json
import asyncio
from openai import OpenAI
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Prompt.prompt_content_generation import blog_generation_prompt,blog_generation_prompt_with_keywords 
from content_generation.utils import json_to_text
# from prompt.social_media_prompt import social_media_prompt
# from utils import convert_doc_to_text
import re
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY")) 
model_name = os.environ.get("OPENAI_MODEL")




def url_agent(items, json_data, keywords=None):

    try:
  
        query = "Generate blog" 
        # json_data = json.loads(json_data)
 
        tone_of_voice_guidelines = json_data.get("Tone of Voice Guidelines", [])
        brand_identity_guidelines = json_data.get("Brand Identity Guidelines", [])
        services_and_offerings_guidelines = json_data.get("Services and Offerings Guidelines", [])
        target_buyer_persona_guidelines = json_data.get("Target Buyer Persona Guidelines", [])

        # Check if keywords exist and are not empty
        if not keywords or (isinstance(keywords, list) and not keywords):
            # Use normal prompt without keywords
            formatted_prompt = blog_generation_prompt.format(
                Tone=tone_of_voice_guidelines,
                Buyer=target_buyer_persona_guidelines,
                Brand=brand_identity_guidelines,    
                Offering=services_and_offerings_guidelines,
                items=items
            )
        else:
            # Use prompt with keywords
            # Handle both old format (list of strings) and new format (dict with Keywords array)
            if isinstance(keywords, dict) and "Keywords" in keywords:
                # New format: extract keyword strings from the structured data
                keyword_list = [kw.get("Keyword", "") for kw in keywords["Keywords"] if kw.get("Keyword")]
                print(f"Keyword list: {keyword_list}")
                formatted_prompt = blog_generation_prompt_with_keywords.format(
                    Tone=tone_of_voice_guidelines,
                    Buyer=target_buyer_persona_guidelines,
                    Brand=brand_identity_guidelines,
                    Offering=services_and_offerings_guidelines,
                    items=items,
                    Keywords=keyword_list
                )
            else:
                # Old format: list of keyword strings
                formatted_prompt = blog_generation_prompt_with_keywords.format(
                    Tone=tone_of_voice_guidelines,
                    Buyer=target_buyer_persona_guidelines,
                    Brand=brand_identity_guidelines,
                    Offering=services_and_offerings_guidelines,
                    items=items,
                    Keywords=keywords
                )

        messages = [
            {'role': 'system', 'content': formatted_prompt},
            {'role': 'user', 'content': query}
        ]

        response = client.chat.completions.create(
            model=model_name, 
            messages=messages, 
            response_format={"type": "json_object"}
        )

        response_content = response.choices[0].message.content
        total_token = response.usage.total_tokens
  
        response_json = json.loads(response_content)
        print(response_json)
        # text_data = json_to_text(response_json)
        # response_json['id'] = 1

        if 'Sections' in response_json and isinstance(response_json['Sections'], list):
            for index, section in enumerate(response_json['Sections'], start=1):
                section['section_id'] = index 

        # print(text_data)
        return response_json, total_token

    except KeyError as e:
        print(f"Key error: {e}. The expected key was not found in the response.")
        return None, "", "", ""
    except json.JSONDecodeError:
        print("Error decoding JSON response.")
        return None, "", "", ""
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None, "", "", ""


def blog_generation(file,json_data, keywords=None):
    text = file
    # if keywords
    try:    
        output, token = url_agent(
            text,
            json_data,
            keywords
        )
        # print(output)   
        return output, token

    except json.JSONDecodeError as e:
        print(f"JSON decoding error in iteration  {str(e)}")
        print(f"Output was: {output}")
    except Exception as e:
        print(f"Error formatting data in iteration  {str(e)}")
