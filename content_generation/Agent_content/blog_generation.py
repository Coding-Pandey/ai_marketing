text = """
Campaign Overview
Early Detection, Lifelong Protection

1. Executive Summary
"Early Detection, Lifelong Protection" is a digital campaign that empowers individuals to take control of their health by leveraging our 99% accurate, non-invasive colon cancer screening test. The campaign’s goal is to highlight that proactive screening today not only prevents complications later but also secures a healthier future. By combining expert endorsements, personalized digital tools, and data-driven messaging, we aim to build trust and drive action among busy professionals who value reliability, efficiency, and comfort.

2. Campaign Objectives
•	Educate and Empower: Inform the target audience about the importance of early detection in preventing advanced disease and improving long-term outcomes.
•	Build Trust: Showcase the clinical rigor and expert validation behind our screening test, emphasizing its 99% accuracy and non-invasive nature.
•	Drive Engagement: Use interactive tools, real patient testimonials, and expert-led content to engage users and encourage them to assess their personal risk.
•	Increase Conversions: Direct interested individuals to dedicated landing pages where they can learn more about the test, schedule screenings, and access additional resources.

3. Target Audience: Proactive Patricia
•	Demographics:
o	Urban professional, ages 40-60
o	High disposable income
o	Likely has a family history of colon cancer or related risk factors
•	Goals & Values:
o	Seeks reliable, fast, non-invasive health screening that fits into her busy lifestyle
o	Values early detection, preventative care, and evidence-backed recommendations
•	Concerns:
o	Dislikes invasive procedures and is cautious about traditional tests
o	Prefers clear, data-driven messaging with endorsements from trusted experts
•	Digital Habits:
o	Active on social media and health apps, participates in online patient communities
o	Enjoys personalized content and interactive tools that help her understand her risk

4. Key Messages
1.	Early Detection is Empowering:
o	"Invest in your future—detect early to protect for life."
2.	99% Accuracy You Can Trust:
o	"Our 99% accurate, non-invasive test is clinically proven to catch colorectal cancer at its earliest stage."
3.	Non-Invasive, Fast, and Convenient:
o	"Skip the discomfort of invasive procedures—our test fits seamlessly into your busy lifestyle."
4.	Personalized Health Insights:
o	"Discover your personalized risk and take control with our interactive health tools."
5.	Expert Endorsements:
o	"Trusted by top oncologists and backed by robust clinical data—our test is your partner in proactive health."

5. Tone of Voice
Our communications maintain a tone that is:
•	Authoritative & Trustworthy:
o	Clear, data-driven language backed by clinical research.
•	Reassuring & Empathetic:
o	Acknowledges patient concerns, offers comfort, and provides risk-free alternatives.
•	Innovative & Forward-Looking:
o	Emphasizes cutting-edge technology and continuous improvement.
•	Accessible & Clear:
o	Avoids technical jargon, ensuring explanations are easy to understand with actionable insights.

"""

summary = {
  "Tone of Voice Guidelines": [
    "Authoritative & Trustworthy: Use clear, evidence-based language backed by scientific research.",
    "Reassuring & Empathetic: Address patient anxiety and emphasize non-invasive procedures to create a compassionate tone.",
    "Innovative & Forward-Looking: Highlight cutting-edge technology and future potential for early cancer detection.",
    "Accessible & Clear: Communicate in plain language, avoiding jargon while ensuring understanding.",
    "Regular updates: Keep messaging relevant by aligning with recent clinical data and developments."
  ],
  "Target Buyer Persona Guidelines": [
    "Proactive Patricia – The Health-Conscious Professional: Values early detection and seeks non-invasive screening options.",
    "Dr. David – The Forward-Thinking Physician: Focuses on reliable testing methods and clinically validated research.",
    "Skeptical Sam – The Health Insurance/Clinic Decision Maker: Aims to reduce healthcare costs and requires strong data to validate decisions.",
    "Common traits include a commitment to preventative care, detailed research needs, and concern for cost-effectiveness.",
    "Communication preferences vary from data-driven, clear messaging to concise executive summaries."
  ],
  "Services and Offerings Guidelines": [
    "Colosafe Darmkrebsfrüherkennungstest: A non-invasive cancer detection test with 99% accuracy, aimed at patients seeking early diagnosis.",
    "13-in-1 PCR: A multiplex PCR assay that detects 13 targets simultaneously for efficient diagnostics.",
    "Key marketing points highlight rapid results, non-invasiveness, and endorsements from leading oncologists.",
    "Each product is positioned to enhance patient outcomes and offers cost efficiency by reducing the need for traditional invasive procedures.",
    "Ongoing innovation and digital integration are emphasized to ensure accessibility and a seamless testing experience."
  ],
  "Brand Identity Guidelines": [
    "Market Leader in Diagnostic Innovation: Position as a pioneer in colon cancer testing through scientific excellence.",
    "Patient Empowerment: Focus on providing reliable, non-invasive tools that foster proactive health management.",
    "Trusted by Medical Experts: Build credibility through endorsements and robust clinical validation.",
    "Future-Forward: Vision of broader adoption and continuous innovation to improve access and sustainability.",
    "All branding elements emphasize emotional connection, scientific rigor, and ongoing engagement with patients and healthcare providers."
  ]
}

import sys
import os
import json
import asyncio
from openai import OpenAI
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Prompt.prompt_content_generation import blog_prompt , summary ,new_promt
# from prompt.social_media_prompt import social_media_prompt
# from utils import convert_doc_to_text
import re
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY")) 
model_name = os.environ.get("OPENAI_MODEL")


# Function to convert JSON to a single text string
def json_to_text(data):
    text = f"Title: {data['Title']}\n\n"
    # text += f"Topic: {data['Topic']}\n\n"
    text += f"Description: {data['Description']}\n\n"
    text += f"Introduction: {data['Introduction']}\n\n"
    text += "Sections:\n"
    for i, section in enumerate(data['Sections'], 1):
        text += f"  {i}. Subheading: {section['Subheading']}\n"
        text += f"     Content: {section['Content']}\n\n"
    text += f"Conclusion: {data['Conclusion']}"
    return text

# Function to parse text back to JSON
def text_to_json(text):
    data = {}
    lines = text.split("\n")
    sections = []
    current_section = {}
    content_flag = False

    for line in lines:
        line = line.strip()
        if line.startswith("Title:"):
            data["Title"] = line.replace("Title:", "").strip()
        elif line.startswith("Topic:"):
            data["Topic"] = line.replace("Topic:", "").strip()
        elif line.startswith("Description:"):
            data["Description"] = line.replace("Description:", "").strip()
        elif line.startswith("Introduction:"):
            data["Introduction"] = line.replace("Introduction:", "").strip()
        elif line.startswith("Sections:"):
            continue
        elif re.match(r"\d+\.\s+Subheading:", line):
            if current_section:
                sections.append(current_section)
            current_section = {"Subheading": line.split("Subheading:")[1].strip()}
            content_flag = False
        elif line.startswith("Content:"):
            current_section["Content"] = line.replace("Content:", "").strip()
            content_flag = True
        elif content_flag and line:
            current_section["Content"] += "\n" + line.strip()
    
    if current_section:
        sections.append(current_section)
    
    data["Sections"] = sections
    data["Conclusion"] = lines[-1].replace("Conclusion:", "").strip() if lines[-1].startswith("Conclusion:") else ""
    
    return data
# print(client)

def url_agent(items, json_data):
 
    try:
        # print(json_data)
        query = "Generate blog" 
        json_data = json.loads(json_data)
 
        tone_of_voice_guidelines = json_data.get("Tone of Voice Guidelines", [])
        brand_identity_guidelines = json_data.get("Brand Identity Guidelines", [])
        services_and_offerings_guidelines = json_data.get("Services and Offerings Guidelines", [])
        target_buyer_persona_guidelines = json_data.get("Target Buyer Persona Guidelines", [])
        
        print(brand_identity_guidelines)
        formatted_prompt = new_promt.format(
            Tone=tone_of_voice_guidelines,
            Buyer=target_buyer_persona_guidelines,
            Brand=brand_identity_guidelines,    
            Offering=services_and_offerings_guidelines,
            items=items
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
        # print(response_content)

        
        response_json = json.loads(response_content)
        text_data = json_to_text(response_json)
        return text_data

    except KeyError as e:
        print(f"Key error: {e}. The expected key was not found in the response.")
        return None, "", "", ""
    except json.JSONDecodeError:
        print("Error decoding JSON response.")
        return None, "", "", ""
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None, "", "", ""


def blog_generation(file,json_data):
    text = file
    try:    
        output = url_agent(
            text, 
            json_data, 
        )
        
    
    except json.JSONDecodeError as e:
        print(f"JSON decoding error in iteration  {str(e)}")
        print(f"Output was: {output}")
    except Exception as e:
        print(f"Error formatting data in iteration  {str(e)}")

    return output


# data = blog_generation(file=text,json_data= summary )

