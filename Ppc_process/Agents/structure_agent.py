import sys
import os
import json
import asyncio
from openai import AsyncOpenAI
from openai import OpenAI
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from clustering_pipeline.k_mean import ClusteringConfig, Cluster
from prompt.structure_prompt import prompt
from utils import extract_first_json_object 
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

# client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))  
client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
model_name = os.environ.get("OPENAI_MODEL_2")
min_clusters = os.environ.get("MIN_CLUSTER")
max_clusters = os.environ.get("MAX_CLUSTER")


async def url_agent(PROMPT=prompt, items=None, Ad_group=None, Ad_headline=None, description=None):
    try:

        query = ""

        formatted_prompt = PROMPT.format(
            keywords_json=json.dumps(items, indent=4)
        )
        
        messages = [
            {'role': 'system', 'content': formatted_prompt},
            {'role': 'user', 'content': query}
        ]

        response = await client.chat.completions.create(
                    model=model_name, 
                    messages=messages, 
                    response_format={"type": "json_object"}
                )
    
        response_content = response.choices[0].message.content
        total_token = response.usage.total_tokens
        output_json = json.loads(response_content) if response_content else []
        print("Response received:", output_json)

        # Extract relevant data
        ad_data = []
        for page in output_json['Pages']:
            Ad_group = page['Ad Group']
            Ad_headline = page['Ad Headline']
            description = page['Description']

        return output_json , Ad_group, Ad_headline, description, total_token

    except Exception as e:
        print(f"Error in url_agent: {e}")
        return None, None, None, 0


def process_clusters(data):
    config = ClusteringConfig(min_clusters=min_clusters, max_clusters=max_clusters)  
    clusterer = Cluster(config)
    metadata_column = "Keyword"

    results, optimal_cluster = clusterer.process_clustering(data, metadata_column)
    print(f"Optimal number of clusters: {optimal_cluster}")
    
  
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
            continue  

    print(f"Found {len(clusters)} clusters")
    return clusters


async def agent_call(cluster_items):
    Ad_group = []
    structured_results = []
    Ad_headline = []
    description = []
    total_token_count = 0
    batch_size = 100
    batches = [cluster_items[i:i+batch_size] for i in range(0, len(cluster_items), batch_size)]
    tasks = []

    # Create tasks for all batches
    for batch in batches:
        print(f"Creating task for batch with {len(batch)} items")
        task = asyncio.create_task(url_agent(
            PROMPT=prompt,
            items=batch,
            Ad_group=Ad_group,
            Ad_headline=Ad_headline,
            description=description
        ))
        tasks.append(task)

    # Run all tasks concurrently
    results = await asyncio.gather(*tasks)

    # Aggregate results
    for structured_data, Ad_group_detail, Ad_headline_detail, description_detail, batch_tokens in results:
        if batch_tokens:
            total_token_count += batch_tokens
            print(f"Batch token count: {batch_tokens}, Running total: {total_token_count}")
        if structured_data:
            structured_results.extend([structured_data] if not isinstance(structured_data, list) else structured_data)
        if Ad_group_detail:
            Ad_group.extend(Ad_group_detail)
        if Ad_headline_detail:
            Ad_headline.extend(Ad_headline_detail)
        if description_detail:
            description.extend(description_detail)      

    print(f"Processed {len(structured_results)} items, structured_results {structured_results}")       

    return structured_results, total_token_count


async def agent_recursion(clusters): 
    cluster_data = process_clusters(clusters)
    final_results = []
    global_token_count = 0 
    for cluster_id, cluster_items in cluster_data.items():
        print(f"Processing cluster {cluster_id} with {len(cluster_items)} items")
        structured_data, cluster_token_count = await agent_call(cluster_items)

        global_token_count += cluster_token_count

        if structured_data:
            for structure in structured_data:
                if isinstance(structure, str):
                    extracted_json = extract_first_json_object(structure)
                    if extracted_json:
                        final_results.append(extracted_json)
                else:
                    final_results.append(structure)
    print(f"Processed {len(final_results)} items", final_results)                
    print(f"Total token usage across all clusters: {global_token_count}")          

    return final_results, global_token_count


# Main entry point to run the code
async def ppc_main(input_data):
    results, total_token_count = await agent_recursion(input_data)
    # Save results to file
    # with open("clustering_results_ppc1.json", "w") as f:
    #     json.dump(results, f, indent=2)
    # print(f"Processed {len(results)} items and saved to clustering_results.json")
    print(f"total token count: {total_token_count}")
    return results, total_token_count



# if __name__ == "__main__":


#     csv_file = r"c:\Users\nickc\OneDrive\Desktop\SEO\ppc_process\data\PPC-test-source.xlsx"  
#     df = pd.read_excel(csv_file)
#     df1 = df[["Keyword"]]
#     # Convert DataFrame to JSON
#     data = df1.to_dict(orient="records")
    
#     # Run the main function
#     asyncio.run(ppc_main(data))