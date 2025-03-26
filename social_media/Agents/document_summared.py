import sys
import os
import json
import asyncio
from openai import OpenAI
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from social_media.prompt.document_summ_prompt import document_summerzition
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY")) 
model_name = os.environ.get("OPENAI_MODEL")


def Document_summerizer(items):
    try:
        query = "" 

        formatted_prompt = document_summerzition.format(
            items=json.dumps(items)
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
        print(response_content)
        response_content = json.loads(response_content)
        return response_content

    except KeyError as e:
        print(f"Key error: {e}. The expected key was not found in the response.")
        return None, "", "", ""
    except json.JSONDecodeError:
        print("Error decoding JSON response.")
        return None, "", "", ""
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None, "", "", ""

    