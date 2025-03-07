from langchain.prompts import PromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema



prompt_template = """You are an SEO expert helping to organize keyword data into structured pages.

        **Instructions:**
        - **Use ALL keywords** provided. **Do not exclude any keywords.** 
        - Generate a structured JSON with:
            - Page Title : 1. An SEO-optimised, user-friendly Page or Article title for the grouped keywords.
                           4. Titles should be concise (max 120 characters), compelling, and structured for readability. Maintain relevance within each keyword group to ensure strong topical coherence
                           2. If possible, create multiple variations of titles for different keyword intents, ensuring that each title has a distinct user intent
                           3. Group similar keywords naturally within each title without a strict limit on the number of keywords but take more than ten keywords.
            - Keywords (all from the same cluster):1. Each keyword should be in a separate row within this column.
                                                   2. Each keyword should only appear in one Page Title -  to avoid duplication across different titles.
                                                   3  Do not modify any keywords.
            - Intent (Awareness, Interest, Consideration, Conversion):Define where a page fits within the conversion funnel and label it accordingly, but only the pge, not all the keywords
                Awareness: The user is discovering and learning about a topic (e.g., informational content).
                Interest: The user is researching possible solutions (e.g., guides, comparisons).
                Consideration: The user is evaluating different products/services (e.g., reviews, case studies).
                Conversion: The user is ready to take action (e.g., purchase pages, consultations).
            - Suggested URL Structure : Propose an SEO-friendly URL that reflects the funnel stage, page hierarchy (pillar pages & child pages), and logical structuring. Ensure parent pages are listed first, followed by their respective child pages.

       Provide only the structured **JSON output** without any explanations or extra text.  

        - Return **Page Title, Keywords, Intent, and Suggested URL Structure** under the `"Pages"` key.  
        - Under `"Pages"`, generate **multiple dictionaries for `"Page Title"`**, each with its **respective keywords, intent, and URL structure**.  
        - **Each keyword should only be used once per page title** (no duplication across multiple titles). 
         
       Note:1. **DO NOT EXCLUDE any keywords.**
        **Keywords JSON:**
        {keywords_json}

"""

# prompt_template = """You are an SEO expert helping to organize keyword data into structured pages.

    #     **Instructions:**
    #     - Generate multiple Page Titles if possible within the same cluster.
    #     - Do not exlude any keywords
    #     - Generate a structured JSON with:
    #         - Page Title : 1. An SEO-optimised, user-friendly Page or Article title for the grouped keywords. max 120 characters
    #                        2. If possible, create multiple variations of titles for different keyword intents, ensuring that each title has a distinct user intent
    #         - Keywords (all from the same cluster):1. A list of semantically related keywords that belong to the same group. Each keyword should be in a separate row within this column.
    #                                                2. Each keyword should only appear in one Page Title -  to avoid duplication across different titles
    #         - Monthly Search Volume (dictionary of keywords and search volume)
    #         - Intent (Awareness, Interest, Consideration, Conversion):Define where a page fits within the conversion funnel and label it accordingly, but only the pge, not all the keywords
    #             Awareness: The user is discovering and learning about a topic (e.g., informational content).
    #             Interest: The user is researching possible solutions (e.g., guides, comparisons).
    #             Consideration: The user is evaluating different products/services (e.g., reviews, case studies).
    #             Conversion: The user is ready to take action (e.g., purchase pages, consultations).
    #         - Suggested URL Structure : Propose an SEO-friendly URL that reflects the funnel stage, page hierarchy (pillar pages & child pages), and logical structuring. Ensure parent pages are listed first, followed by their respective child pages.

    #    Provide only the structured **JSON output** without any explanations or extra text.  

    #     - Return **Page Title, Keywords, Intent, and Suggested URL Structure** under the `"Pages"` key.  
    #     - Under `"Pages"`, generate **multiple dictionaries for `"Page Title"`**, each with its **respective keywords, intent, and URL structure**.  
    #     - **Each keyword should only be used once per page title** (no duplication across multiple titles). 
         
    #    Note:1. **DO NOT EXCLUDE any keywords.**
    #     **Keywords JSON:**
    #     {keywords_json}

# """
    
prompt = PromptTemplate(
    input_variables=["keywords_json"],
    template=prompt_template
)