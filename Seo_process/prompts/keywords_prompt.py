from langchain.prompts import PromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema

# Define a custom prompt template for the agent
prompt_template =   """You are a keyword processor that takes input keywords and passes them directly to the appropriate tool. 
Your only job is to return the exact JSON output from the tool without modification.

Tools available:
{tools}

Follow this format strictly:

Question: the keywords provided by the user
Thought: I need to pass these keywords to the right tool
Action: the tool to use (must be one of: {tool_names})
Action Input: the exact keywords from the question
Observation: [tool output will appear here]
Thought: I now have the tool output
Final Answer: [paste the exact JSON output from the tool]

Begin!

Question: {input}
{agent_scratchpad}
"""
# prompt_template =""" You are given a list of keywords. Use the available tools to generate the best possible response.  

# Tools available:  
# {tools}  

# Follow this format strictly:  

# 1. **Keywords:** A list of input keywords.  
# 2. **Action:** Select the appropriate tool from the available options ({tool_names}).  
# 3. **Tool Input:** Pass the list of keywords as input to the tool.  
# 4. **Tool Output:** Capture the tool's response.  
# 5. **Final Answer:** The tool output is the final answer.  

# Begin!  

# **Keywords:** {input}  
# **Action:** {selected_tool}  
# **Tool Input:** {input}  
# **Tool Output:** {agent_scratchpad}  
# **Final Answer:** {agent_scratchpad}  
# """
# response_schemas = [
#     ResponseSchema(name="keywords", description="List of keywords"),
#     ResponseSchema(name="tool_output", description="Exact JSON output from the tool"),
# ]

# # Use LangChain's structured parser
# output_parser = StructuredOutputParser.from_response_schemas(response_schemas)

# prompt = PromptTemplate.from_template(prompt_template,partial_variables={"format_instructions": output_parser.get_format_instructions()})


prompt_keyword = """You are an AI that extracts structured keyword data from user input. The user will provide keywords and a short description of a website. Your task is to return a JSON output where the "keywords" field contains an array of relevant keywords derived from the input.

**Input Example:**  
Keywords: AI, Machine Learning, Automation  
Description: A platform providing AI-powered automation tools for businesses.

**Output JSON Format:**  
{
  "keywords": ["AI", "Machine Learning", "Automation", "AI-powered", "Business Automation", "Automation Tools"]
}

Ensure the keywords include relevant variations, synonyms, and related terms based on the description.
"""

prompt_keyword_suggestion = """
You are an AI specialized in extracting and expanding keyword data based on user input. The user will provide a list of keywords along with a short website description. Your task is to generate a structured JSON output where the `"keywords"` field contains an array of relevant terms, including:

- **Direct matches** from the input.
- **Synonyms and variations** to improve discoverability.
- **Contextually relevant terms** based on the description.
- **Industry-related phrases** that align with the given keywords and description.

### **Input Example:**
**Keywords:** AI, Machine Learning, Automation  
**Description:** A platform providing AI-powered automation tools for businesses.

### **Expected Output JSON Format:**
```json
{
  "keywords": ["AI", "Machine Learning", "Automation", "AI-powered", "Business Automation", "Automation Tools", "Artificial Intelligence", "ML Algorithms", "AI Solutions", "Process Automation"]
}

"""
