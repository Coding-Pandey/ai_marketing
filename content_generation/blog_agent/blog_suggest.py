import sys
import os
import json
import asyncio
from openai import OpenAI
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Prompt.prompt_content_generation import blog_suggest_prompt 
# from content_generation.utils import json_to_text
# from prompt.social_media_prompt import social_media_prompt
# from utils import convert_doc_to_text
import re
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY")) 
model_name = os.environ.get("OPENAI_MODEL")



def url_agent(items, json_data, Generated_Blog):
 
    try:
  
        query = "Generate new Section" 
        # json_data = json.loads(json_data)
 
        tone_of_voice_guidelines = json_data.get("Tone of Voice Guidelines", [])
        brand_identity_guidelines = json_data.get("Brand Identity Guidelines", [])
        services_and_offerings_guidelines = json_data.get("Services and Offerings Guidelines", [])
        target_buyer_persona_guidelines = json_data.get("Target Buyer Persona Guidelines", [])
        
       
        formatted_prompt = blog_suggest_prompt.format(
            Tone=tone_of_voice_guidelines,
            Buyer=target_buyer_persona_guidelines,
            Brand=brand_identity_guidelines,    
            Offering=services_and_offerings_guidelines,
            Generated_Blog=Generated_Blog,
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


def blog_suggest(file,json_data, Generated_Blog):
    text = file
    Generated_Blog = json.dumps(Generated_Blog)
    try:    
        output, token = url_agent(
            text, 
            json_data, 
            Generated_Blog
        )
        # print(output)   
        return output, token

    except json.JSONDecodeError as e:
        print(f"JSON decoding error in iteration  {str(e)}")
        print(f"Output was: {output}")
    except Exception as e:
        print(f"Error formatting data in iteration  {str(e)}")


# text = """
# Campaign Overview
# Early Detection, Lifelong Protection

# 1. Executive Summary
# "Early Detection, Lifelong Protection" is a digital campaign that empowers individuals to take control of their health by leveraging our 99% accurate, non-invasive colon cancer screening test. The campaign’s goal is to highlight that proactive screening today not only prevents complications later but also secures a healthier future. By combining expert endorsements, personalized digital tools, and data-driven messaging, we aim to build trust and drive action among busy professionals who value reliability, efficiency, and comfort.

# 2. Campaign Objectives
# Educate and Empower: Inform the target audience about the importance of early detection in preventing advanced disease and improving long-term outcomes.
# Build Trust: Showcase the clinical rigor and expert validation behind our screening test, emphasizing its 99% accuracy and non-invasive nature.
# Drive Engagement: Use interactive tools, real patient testimonials, and expert-led content to engage users and encourage them to assess their personal risk.
# Increase Conversions: Direct interested individuals to dedicated landing pages where they can learn more about the test, schedule screenings, and access additional resources.

# 3. Target Audience: Proactive Patricia
# Demographics:
# Urban professional, ages 40-60
# High disposable income
# Likely has a family history of colon cancer or related risk factors
# Goals & Values:
# Seeks reliable, fast, non-invasive health screening that fits into her busy lifestyle
# Values early detection, preventative care, and evidence-backed recommendations
# Concerns:
# Dislikes invasive procedures and is cautious about traditional tests
# Prefers clear, data-driven messaging with endorsements from trusted experts
# Digital Habits:
# Active on social media and health apps, participates in online patient communities
# Enjoys personalized content and interactive tools that help her understand her risk

# """

# Generated_Blog = {
#   'Title': 'Unpacking Cybersecurity: Threats, Trends, and Best Practices',
#   'Description': 'Explore the pressing issue of cybersecurity, uncovering potential threats, the latest trends, and actionable best practices for individuals and organizations to enhance their security posture.',
#   'Introduction': 'In a world increasingly dominated by technology, cybersecurity has become a critical subject for businesses and individuals alike. As cyber threats evolve in sophistication and frequency, understanding these challenges is essential for protecting sensitive data and maintaining trust. This blog delves into the latest trends in cybersecurity and offers practical steps to bolster your defenses.',
#   'Sections': [
#     {
#       'Subheading': 'Problem Overview and Implications',
#       'Content': "Cybersecurity threats have skyrocketed in recent years, with a report indicating that cyberattacks are increasing by 15% annually. From ransomware to data breaches, no sector is safe, with small and large organizations alike falling prey to these malicious incursions. The implications of inadequate cybersecurity measures extend beyond immediate financial losses; they also damage reputations and erode customer trust. A well-publicized breach can leave lasting scars on a brand's image, increasing the urgency for organizations to prioritize cybersecurity strategies."
#     },
#     {
#       'Subheading': 'Key Points or Arguments',
#       'Content': '1. Increased Incidence of Ransomware: Ransomware attacks have surged by over 200% in the last two years, often targeting critical infrastructure and causing operational disruptions. Organizations must integrate backup strategies and incident response plans to mitigate the impact of such attacks.\n\n2. Social Engineering Attacks: Techniques like phishing remain prevalent, with nearly 80% of security incidents stemming from human error. Training employees to recognize and report suspicious activities can drastically reduce risks.\n\n3. The Rise of AI in Cybersecurity: Leveraging artificial intelligence can enhance threat detection and response times, though it also introduces new vulnerabilities. Organizations should stay informed about these emerging technologies to stay ahead of potential exploits.'
#     },
#     {
#       'Subheading': 'Data, Evidence, or Expert Opinions',
#       'Content': 'According to the Cybersecurity and Infrastructure Security Agency (CISA), organizations experienced a 300% increase in attempted cyberattacks during the COVID-19 pandemic as hackers exploited remote work vulnerabilities. Additionally, a recent survey revealed that over 70% of executives believe that their current security measures are insufficient to combat rising threats. Security experts recommend a multi-layered defense, combining advanced technology with human intelligence to create a robust defense strategy.'
#     },
#     {
#       'Subheading': 'Counterarguments or Common Misconceptions',
#       'Content': 'Some may argue that investing in cybersecurity is unnecessary, especially for smaller businesses that may not perceive themselves as targets. However, over 40% of cyberattacks target small firms, proving that scam artists often see them as easier targets due to limited resources. Additionally, many believe that compliance with regulations alone guarantees security. Consequently, organizations must treat compliance as a baseline while continuously improving their defenses beyond mere legal obligations.'
#     },
#     {
#       'Subheading': 'Actionable Steps or Best Practices',
#       'Content': '1. Conduct Regular Security Audits: Assess your security posture and identify potential vulnerabilities regularly. This proactive approach allows you to address weaknesses before they are exploited.\n\n2. Implement Multi-Factor Authentication (MFA): MFA adds an extra layer of protection beyond passwords, making it significantly more challenging for unauthorized users to access systems.\n\n3. Provide Employee Training: Equip your staff with the knowledge to recognize phishing attempts and suspicious activities. Human error is often the weakest link in cybersecurity defenses.\n\n4. Develop an Incident Response Plan: Prepare for the unknown by having a clear and documented response plan in the event of a data breach or cybersecurity incident. Ensure that team members know their roles and responsibilities.'
#     }
#   ],
#   'Conclusion': 'Strengthen Your Cyber Defenses: As cyber threats continue to evolve and diversify, the importance of a strong cybersecurity posture cannot be overstated. By understanding the landscape, investing in proper security measures, and training employees, individuals and organizations can take definitive steps to protect themselves against the growing tide of cybercrime.'
# }

# json_data = {}

# post = blog_suggest(text, json_data, Generated_Blog)       
