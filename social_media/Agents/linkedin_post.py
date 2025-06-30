import sys
import os
import json
import asyncio
from openai import OpenAI
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from social_media.prompt.social_media_prompt import linkedIn_prompt
from social_media.utils import clean_post_list
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY")) 
model_name = os.environ.get("OPENAI_MODEL_2")

def linkedIn_agent(items, json_data, previous_summaries=None):
 
    previous_summaries = previous_summaries if previous_summaries is not None else []

    try:
        # print(json_data)
        query = "Generate a social media post for a campaign. Given the previous Linkedin summary: {previous_summaries}, try to generate a new linkedin (Title, content)" 
        # json_data = json.loads(json_data)
        # Extracting into separate variables
        tone_of_voice_guidelines = json_data.get("Tone of Voice Guidelines", [])
        brand_identity_guidelines = json_data.get("Brand Identity Guidelines", [])
        services_and_offerings_guidelines = json_data.get("Services and Offerings Guidelines", [])
        target_buyer_persona_guidelines = json_data.get("Target Buyer Persona Guidelines", [])

        formatted_prompt = linkedIn_prompt.format(
            Tone=tone_of_voice_guidelines,
            Buyer=target_buyer_persona_guidelines,
            Brand=brand_identity_guidelines,    
            Offering=services_and_offerings_guidelines,
            # hash_tag=hash_tag,
            # emoji=emoji,
            items=items
        )
        
        # print(formatted_prompt)
        formatted_query = query.format(
            previous_summaries=", ".join(previous_summaries) if previous_summaries else "None",
      
        )
        # print(formatted_query)
        messages = [
            {'role': 'system', 'content': formatted_prompt},
            {'role': 'user', 'content': formatted_query}
        ]

        response = client.chat.completions.create(
            model=model_name, 
            messages=messages, 
            response_format={"type": "json_object"}
        )

        response_content = response.choices[0].message.content

        total_token = response.usage.total_tokens
        print(response_content)

        

        response_json = json.loads(response_content)
        if not response_json or "Posts" not in response_json:
            print("Response missing expected 'Posts' structure")
            print(f"Received: {response_content[:200]}...") 
            return None, ""
            
   
        posts = response_json.get("Posts", {})
        print(posts)
        linkedin_data = posts.get("LinkedIn", {})      
        summary = linkedin_data.get("Summary", "")

        return response_content, summary, total_token

    except KeyError as e:
        print(f"Key error: {e}. The expected key was not found in the response.")
        return None, ""
    except json.JSONDecodeError:
        print("Error decoding JSON response.")
        return None, ""
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None, ""


def linkedIn_agent_call( text,json_data ,num_iterations=5, hash_tag=False, emoji=False):
    all_data = []
    previous_summaries = []

    
    try:
        text = text
        # print(text)
    except FileNotFoundError as e:
        return f"File not found: {str(e)}"
    # text = file
    post_index = 1
    token = 0
    for i in range(num_iterations):
        print(f"Iteration {i+1}/{num_iterations}")
        
        output, summary, tokens= linkedIn_agent(
            text, 
            json_data, 
            previous_summaries
        )
        if output is None:
            print(f"Iteration {i+1} failed. Skipping to next iteration.")
            continue
            
        try:
            print(f"Raw output from url_agent: {output[:100]}...") 
       
            output_json = json.loads(output)
            print(f"Parsed output type: {type(output_json)}")
            # print(f"Parsed output content: {output_json}")
            page_id_counter = 1
            linkedin_id = f"{page_id_counter}.{post_index}"
            posts = output_json["Posts"]
            formatted_data = {
                "linkedin_id": linkedin_id,
                "discription": [f"{posts['LinkedIn']['title']}\n\n{posts['LinkedIn']['content']}"],
                "image":None,
                "isSchedule": False,
                "Image_Headline": [posts["LinkedIn"]["Image Headline"]],
                "Subheadline": [posts["LinkedIn"]["Subheadline"]]
            }

            previous_summaries.append(summary)
            all_data.append(formatted_data)
            post_index += 1
            token += tokens

            print(f"Successfully processed iteration {i+1}")
        except json.JSONDecodeError as e:
            print(f"JSON decoding error in iteration {i+1}: {str(e)}")
            print(f"Output was: {output}")
        except TypeError as e:
            print(f"Type error in iteration {i+1}: {str(e)}")
            print(f"Parsed output: {output_json}")
        except Exception as e:
            print(f"Error formatting data in iteration {i+1}: {str(e)}")

    if hash_tag == False and emoji == False:
        return all_data , token

    clean_data = clean_post_list(all_data, remove_emojis=emoji, remove_hashtags=hash_tag)

    return clean_data , token


