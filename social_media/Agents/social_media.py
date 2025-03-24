import sys
import os
import json
import asyncio
from openai import OpenAI
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from social_media.prompt.social_media_prompt import social_media_prompt
from social_media.utils import convert_doc_to_text
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY")) 
model_name = os.environ.get("OPENAI_MODEL_2")

# print(client)

def url_agent(items, previous_summaries=None, previous_Facebooks=None, previous_Twitters=None):
 
    previous_summaries = previous_summaries if previous_summaries is not None else []
    previous_Facebooks = previous_Facebooks if previous_Facebooks is not None else []
    previous_Twitters = previous_Twitters if previous_Twitters is not None else []

    try:
        query = "Generate a social media post for a campaign. Given the previous Linkedin summary: {previous_summaries}, Facebook content: {previous_Facebooks} and Twitter content: {previous_Twitters} try generating a new post." 

   
        formatted_prompt = social_media_prompt.format(
            items=items
        )
        
     
        formatted_query = query.format(
            previous_summaries=", ".join(previous_summaries) if previous_summaries else "None",
            previous_Facebooks=", ".join(previous_Facebooks) if previous_Facebooks else "None",
            previous_Twitters=", ".join(previous_Twitters) if previous_Twitters else "None"
        )

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
        print(response_content)

        

        response_json = json.loads(response_content)
        if not response_json or "Posts" not in response_json:
            print("Response missing expected 'Posts' structure")
            print(f"Received: {response_content[:200]}...") 
            return None, "", "", ""
            
   
        posts = response_json.get("Posts", {})
        linkedin_data = posts.get("LinkedIn", {})
        facebook_data = posts.get("Facebook", {})
        twitter_data = posts.get("Twitter", {})
        
        summary = linkedin_data.get("Summary", "")
        facebook_content = facebook_data.get("content", "")
        twitter_content = twitter_data.get("content", "")

        return response_content, summary, facebook_content, twitter_content

    except KeyError as e:
        print(f"Key error: {e}. The expected key was not found in the response.")
        return None, "", "", ""
    except json.JSONDecodeError:
        print("Error decoding JSON response.")
        return None, "", "", ""
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None, "", "", ""


def agent_call( file,file_name, num_iterations=5):
    all_data = []
    previous_summaries = []
    previous_Facebooks = []
    previous_Twitters = []
    
    try:
        text = convert_doc_to_text(file,file_name)
        print(text)
    except FileNotFoundError as e:
        return f"File not found: {str(e)}"

    for i in range(num_iterations):
        print(f"Iteration {i+1}/{num_iterations}")
        
        output, summary, facebook, twitter = url_agent(
            # promptt, 
            text, 
            previous_summaries, 
            previous_Facebooks, 
            previous_Twitters
        )
        if output is None:
            print(f"Iteration {i+1} failed. Skipping to next iteration.")
            continue
            
        try:
            print(f"Raw output from url_agent: {output[:100]}...") 
       
            output_json = json.loads(output)
            print(f"Parsed output type: {type(output_json)}")
            # print(f"Parsed output content: {output_json}")
            
            posts = output_json["Posts"]
            formatted_data = {
                "LinkedIn": [f"{posts['LinkedIn']['title']}\n\n{posts['LinkedIn']['content']}"],
                "Facebook": [facebook],
                "Twitter": [twitter],
                "Image Headline": [posts["LinkedIn"]["Image Headline"]],
                "Subheadline": [posts["LinkedIn"]["Subheadline"]]
            }

            previous_summaries.append(summary)
            previous_Facebooks.append(facebook)
            previous_Twitters.append(twitter)

            all_data.append(formatted_data)
            print(f"Successfully processed iteration {i+1}")
        except json.JSONDecodeError as e:
            print(f"JSON decoding error in iteration {i+1}: {str(e)}")
            print(f"Output was: {output}")
        except TypeError as e:
            print(f"Type error in iteration {i+1}: {str(e)}")
            print(f"Parsed output: {output_json}")
        except Exception as e:
            print(f"Error formatting data in iteration {i+1}: {str(e)}")
    
    return all_data


# data = agent_call(text, num_iterations=10)