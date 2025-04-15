import sys
import os
import json
import asyncio
from openai import OpenAI
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from clustering_pipeline.k_mean import ClusteringConfig, Cluster 
from Seo_process.prompts.cluster_URL_prompt import prompt  
from utils import extract_first_json_object  
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))  
model_name = os.environ.get("OPENAI_MODEL_2")
min_clusters = os.environ.get("MIN_CLUSTER")
max_clusters = os.environ.get("MAX_CLUSTER")
# type(max_clusters)
async def url_agent(PROMPT, items, previous_page_titles=None, previous_URL=None):
    try:
    
        query = "Used all keywords for createing Page title and used same language as keywords. Given the previous page titles: {previous_titles} and their respective URLs: {previous_URL}, generate a new page title for the next keyword while maintaining the hierarchical structure. If a keyword is related to an existing title, use that title and URL as a reference to form a structured, topic-clustered page title (pillar pages & child pages). Ensure consistency in naming conventions and logical grouping."
        print("previous_page_titles:", previous_page_titles)

        formatted_prompt = PROMPT.format(
            keywords_json=json.dumps(items, indent=4)
        )
        
        formatted_query = query.format(
            previous_titles=json.dumps(previous_page_titles or [], indent=4),
            previous_URL=json.dumps(previous_URL or [], indent=4)
            
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
        total_token = response.usage.total_tokens

        output_json = json.loads(response_content) if response_content else []
        print("Response received:", output_json)

    
        page_titles = []
        url_structures = []
        
        # Case 1: Direct array of page objects
        if isinstance(output_json, list):
            for item in output_json:
                if isinstance(item, dict):
                    if "Page Title" in item:
                        page_titles.append(item["Page Title"])
                    if "Suggested URL Structure" in item:
                        url_structures.append(item["Suggested URL Structure"])
                elif isinstance(item, str):
                    # Try to extract JSON from string
                    json_obj = extract_first_json_object(item)
                    if json_obj:
                        if "Page Title" in json_obj:
                            page_titles.append(json_obj["Page Title"])
                        if "Suggested URL Structure" in json_obj:
                            url_structures.append(json_obj["Suggested URL Structure"])
        
        # Case 2: 'Pages' key containing array of page objects
        elif isinstance(output_json, dict):
            if "Pages" in output_json and isinstance(output_json["Pages"], list):
                for page in output_json["Pages"]:
                    if isinstance(page, dict):
                        if "Page Title" in page:
                            page_titles.append(page["Page Title"])
                        if "Suggested URL Structure" in page:
                            url_structures.append(page["Suggested URL Structure"])
            
            # Case 3: 'results' key containing array
            elif "results" in output_json and isinstance(output_json["results"], list):
                for item in output_json["results"]:
                    if isinstance(item, dict):
                        if "Page Title" in item:
                            page_titles.append(item["Page Title"])
                        if "Suggested URL Structure" in item:
                            url_structures.append(item["Suggested URL Structure"])
        
        print("Page titles extracted:", page_titles)
        print("URL structures extracted:", url_structures)
          
   
        return output_json, page_titles, url_structures, total_token

    except Exception as e:
        print(f"Error in url_agent: {e}")
        return None, None, None,0


def process_clusters(data):
    # config = ClusteringConfig(min_clusters=int(min_clusters), max_clusters=int(max_clusters)) 
    clusterer = Cluster()
    metadata_column = "Keyword"

    results, optimal_cluster = clusterer.process_clustering(data, metadata_column)
    print(f"Optimal number of clusters: {optimal_cluster}")
    
    # Handle results as string or dict
    if isinstance(results, str):
        results = json.loads(results)

    clusters = {}
    for item in results:
        if "cluster" in item:  
            cluster_id = item["cluster"]
            item_copy = {k: v for k, v in item.items() if k != "cluster"} 

            if cluster_id not in clusters:
                clusters[cluster_id] = []

            clusters[cluster_id].append(item_copy)
        else:
            print(f"Warning: Item missing cluster key: {item}")
            continue  # Skip instead of raising exception

    print(f"Found {len(clusters)} clusters")
    return clusters


async def agent_call(cluster_items):
    previous_page_titles = []
    structured_results = []
    previous_structured_URL = []
    total_token_count = 0

    # Process in batches of 100
    for i in range(0, len(cluster_items), 100): 
        batch = cluster_items[i:i+100]  
        print(f"Processing batch {i//100 + 1} with {len(batch)} items")
        
        # Pass previous page titles to url_agent
        structured_data, batch_page_titles, url_structure, batch_tokens  = await url_agent(
            PROMPT=prompt,
            items=batch, 
            previous_page_titles=previous_page_titles,
            previous_URL=previous_structured_URL
        )
        # Accumulate token count for this cluster
        if batch_tokens:
            total_token_count += batch_tokens
            print(f"Batch token count: {batch_tokens}, Running total: {total_token_count}")

        if structured_data:
            structured_results.extend([structured_data] if not isinstance(structured_data, list) else structured_data)

        if batch_page_titles:
            previous_page_titles.extend(batch_page_titles)  

        if url_structure:
            previous_structured_URL.extend(url_structure) 
   

    print(f"Processed {len(structured_results)} items, structured_results {structured_results}")       

    return structured_results, total_token_count


async def agent_recursion(clusters): 
    cluster_data = process_clusters(clusters)
    final_results = []
    global_token_count = 0 
    for cluster_id, cluster_items in cluster_data.items():
        print(f"Processing cluster {cluster_id} with {len(cluster_items)} items")
        structured_data, cluster_token_count  = await agent_call(cluster_items)

        global_token_count += cluster_token_count

        if structured_data:
            for structure in structured_data:
                if isinstance(structure, str):
                    extracted_json = extract_first_json_object(structure)
                    if extracted_json:
                        final_results.append(extracted_json)
                else:
                    # Already a dict/JSON object
                    final_results.append(structure)
    print(f"Processed {len(final_results)} items", final_results)      
    print(f"Total token usage across all clusters: {global_token_count}")          

    return final_results, global_token_count


# Main entry point to run the code
async def seo_main(input_data):
    results, total_token_count = await agent_recursion(input_data)
    # Save results to file
    # with open("clustering_results1.json", "w") as f:
    #     json.dump(results, f, indent=2)
    # print(f"Processed {len(results)} items and saved to clustering_results.json")
    print(f"Total token count: {total_token_count}")
    return results, total_token_count


# # Example of how to run the code
# if __name__ == "__main__":
#     # Load your input data here
#     # Example:
#     # with open("input_data.json", "r") as f:
#     #     input_data = json.load(f)
    
#     # For testing purposes, create a simple dataset
#     csv_file = r"C:\Users\nickc\Downloads\dhs kwr test.csv"  # Replace with your file path
#     df = pd.read_csv(csv_file)
#     df1 = df[["Keyword"]]
#     # Convert DataFrame to JSON
#     data = df1.to_dict(orient="records")
    
#     # Run the main function
#     asyncio.run(seo_main(data))