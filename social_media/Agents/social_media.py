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

def url_agent(items, json_data,previous_summaries=None, previous_Facebooks=None, previous_Twitters=None):
 
    previous_summaries = previous_summaries if previous_summaries is not None else []
    previous_Facebooks = previous_Facebooks if previous_Facebooks is not None else []
    previous_Twitters = previous_Twitters if previous_Twitters is not None else []

    try:
        query = "Generate a social media post for a campaign. Given the previous Linkedin summary: {previous_summaries}, Facebook content: {previous_Facebooks} and Twitter content: {previous_Twitters} try generating a new post." 

   
        formatted_prompt = social_media_prompt.format(
            summarized_text=json_data,
            items=items
        )
        
        print(formatted_prompt)
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


def agent_call( file,file_name,json_data, num_iterations=5):
    all_data = []
    previous_summaries = []
    previous_Facebooks = []
    previous_Twitters = []
    
    try:
        text = convert_doc_to_text(file,file_name)
        print(text)
    except FileNotFoundError as e:
        return f"File not found: {str(e)}"
    # text = file
    for i in range(num_iterations):
        print(f"Iteration {i+1}/{num_iterations}")
        
        output, summary, facebook, twitter = url_agent(
            text, 
            json_data, 
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

# text ="""
# Plug & Play, Grow
# Campaign Overview
# Tagline:
# “Plug in, play fast, grow.”
# Core Idea:
# Replace the complexity and high costs of an in‑house marketing team with a ready‑to‑deploy, plug‑and‑play solution that delivers expert multi‑channel campaigns for just £5,000 per month. Our system—steeped in our organic tech identity—blends strategic creativity with digital precision. While subtle AI automation underpins efficiency, our primary promise is that you free up your internal bandwidth to focus on big‑picture strategy and growth.

# Campaign Objectives
# Secure a Meeting:
# Goal: Engage Growth‑Focused Marketing Managers by showcasing our Accelerator service in a discovery call.
# Metric: Generate at least 15 qualified leads per month through targeted outreach, aiming for a 50% conversion rate into booked meetings.


# Sign the Contract:
# Goal: Convert 30% of discovery calls into signed contracts for the £5,000/month Accelerator service.
# Metric: Secure new contracts by demonstrating tangible ROI and cost‑efficiency, with a focus on how our solution outperforms an in‑house team costing £20K–£30K/month.


# Demonstrate Cost Savings & Value:
# Goal: Clearly communicate that our £5K/month plug‑and‑play solution delivers the same (or superior) multi‑channel marketing outcomes as a costly in‑house team.
# Metric: Use interactive infographics and cost‑comparison tools to educate prospects—targeting at least 70% recognition of the value differential during meetings.



# Target Buyer Persona
# The Growth‑Focused Marketing Manager
# Profile Highlights:
# Role: Marketing Manager or Head of Marketing in a company with 20–50 employees (often in a scale‑up phase).
# Budget: Possesses a moderate, flexible marketing budget and values cost‑efficiency.
# Team: Works with a small, established marketing team (often including a social media specialist, content writer, or junior marketer).
# Pain Points:
# Struggles to scale campaigns due to limited internal bandwidth and expertise.
# Needs advanced tactics (like retargeting, A/B testing, and integrated reporting) but lacks resources for full‑time execution.
# Faces pressure from leadership to drive pipeline growth and reduce cost per acquisition (CPA).
# Goals & Motivations:
# Aims to develop a robust inbound pipeline and enhance brand visibility.
# Seeks a partner who can handle execution details, allowing them to focus on strategic planning.
# Buying Triggers:
# Recent funding or revenue growth necessitates an expansion in marketing efforts.
# Leadership demands more efficient, measurable growth without compromising quality.
# Our messaging is tailored to resonate with these managers—providing a clear, cost‑efficient solution that eases their execution bottlenecks while driving measurable results.

# Creative & Messaging Concept
# Key Messaging Pillars:
# Speed & Simplicity: “No lengthy hiring process. Plug in our expert team and start growing immediately.”


# Cost‑Efficiency: “For only £5K/month, replace a team that would cost £20K–£30K/month, without compromising on quality.”


# Strategic Partnership: “Let our specialized team become your growth accelerator—handling execution while you focus on strategy.”
# While our advanced AI automation subtly powers our systems to optimize retargeting, A/B testing, and analytics, the emphasis is on delivering measurable, high‑quality results without the overhead of an in‑house team.

# """
# # data = agent_call(text, num_iterations=10)

# json_data ={"Tone of Voice Guidelines": {
#     "Core attributes": [
#         "Balance of natural warmth with digital precision.",
#         "Authoritative yet empathetic communication style.",
#         "Break complex ideas into clear segments using natural metaphors.",
#         "Evolve the tone to match client journey, integrating organic and automated approaches."
#     ],
#     "Language and Vocabulary": [
#         "Use nature-inspired language alongside technical digital terms.",
#         "Craft messaging that simplifies complex marketing demands for target personas.",
#         "Adapt language to align with the audience's technical sophistication and needs."
#     ],
#     "Addressing Buyer Pain Points": [
#         "Acknowledge challenges in sustaining lead flow and managing digital tools.",
#         "Highlight transparent ROI and measurable outcomes.",
#         "Create messaging that reassures clients about support and growth."
#     ]
# },
# "Target Buyer Persona Guidelines": {
#     "Persona 1: Ben Hardy – The Scrappy Startup Founder": [
#         "Position: Founder/CEO, with fewer than 20 employees.",
#         "Pain Points: Limited resources to run sophisticated marketing campaigns.",
#         "Goals: Grow sales and establish online presence cost-effectively."
#     ],
#     "Persona 2: The Growth-Focused Marketing Manager": [
#         "Position: Marketing Manager at a scaling company with 20-50 employees.",
#         "Pain Points: Lacks internal expertise for multi-channel execution.",
#         "Goals: Develop inbound leads and build brand authority."
#     ],
#     "Persona 3: The Strategic Marketing Director/CMO": [
#         "Position: CMO or Marketing Director at companies with 50-250+ employees.",
#         "Pain Points: Needs advanced strategies and accountability.",
#         "Goals: High-volume lead generation and unification of marketing channels."
#     ]
# },
# "Services and Offerings Guidelines": {
#     "Offering 1: Tier 1 – Essentials": [
#         "Price: £2,500 / $3,100 per month.",
#         "Target Audience: Small to mid-sized businesses.",
#         "Core Services: SEO, organic social media management, essential PPC management, and website development."
#     ],
#     "Offering 2: Tier 2 – Accelerator": [
#         "Price: £5,000 / $6,200 per month.",
#         "Target Audience: Growing companies for multi-channel expansion.",
#         "Core Services: In-depth market analysis, advanced AI SEO, and expanded PPC management."
#     ],
#     "Offering 3: Tier 3 – Enterprise": [
#         "Price: £10,000+ / $12,500+ per month (customized).",
#         "Target Audience: Larger businesses with complex marketing needs.",
#         "Core Services: AI-powered strategic planning, high-volume content production, and advanced marketing automation."
#     ]
# },
# "Brand Identity Guidelines": {
#     "Core Theme": [
#         "Organic Tech/Fusion of Nature and Digital Elements.",
#         "Blend of nurturing growth with technical precision.",
#         "Communicates a balanced approach in digital marketing."
#     ],
#     "Visual Identity": [
#         "Imagery that combines natural growth elements with digital motifs.",
#         "Warm earthy tones paired with modern digital accents.",
#         "Typography that balances organic forms with modern legibility."
#     ],
#     "Implementation Strategies": [
#         "Website featuring interactive visuals of growth progression.",
#         "Physical and digital marketing collateral that illustrate client journeys.",
#         "Develop messaging that embodies the organic-tech narrative."
#     ]
# }
# }


# data = agent_call(file=text,json_data= json_data ,num_iterations=2)