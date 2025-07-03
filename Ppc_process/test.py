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
        return None, None, None, None, 0


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


async def agent_call_sequential(cluster_items, batch_size=100):
    """Process batches sequentially for large batch sizes"""
    Ad_group = []
    structured_results = []
    Ad_headline = []
    description = []
    total_token_count = 0
    
    batches = [cluster_items[i:i+batch_size] for i in range(0, len(cluster_items), batch_size)]
    
    # Process batches sequentially
    for i, batch in enumerate(batches):
        print(f"Processing batch {i+1}/{len(batches)} sequentially with {len(batch)} items")
        
        structured_data, Ad_group_detail, Ad_headline_detail, description_detail, batch_tokens = await url_agent(
            PROMPT=prompt,
            items=batch,
            Ad_group=Ad_group,
            Ad_headline=Ad_headline,
            description=description
        )
        
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

    print(f"Processed {len(structured_results)} items sequentially")
    return structured_results, total_token_count


async def agent_call_concurrent(cluster_items, batch_size=100):
    """Process batches concurrently for smaller batch sizes"""
    Ad_group = []
    structured_results = []
    Ad_headline = []
    description = []
    total_token_count = 0
    
    batches = [cluster_items[i:i+batch_size] for i in range(0, len(cluster_items), batch_size)]
    tasks = []

    # Create tasks for all batches
    for batch in batches:
        print(f"Creating concurrent task for batch with {len(batch)} items")
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

    print(f"Processed {len(structured_results)} items concurrently")
    return structured_results, total_token_count


async def agent_call(cluster_items, batch_size=100):
    """Main function to decide between sequential or concurrent processing"""
    if batch_size > 100:
        print(f"Batch size {batch_size} > 100, processing sequentially")
        return await agent_call_sequential(cluster_items, batch_size)
    else:
        print(f"Batch size {batch_size} <= 100, processing concurrently")
        return await agent_call_concurrent(cluster_items, batch_size)


async def process_single_cluster(cluster_id, cluster_items, batch_size=100):
    """Process a single cluster with specified batch size"""
    print(f"Processing cluster {cluster_id} with {len(cluster_items)} items")
    structured_data, cluster_token_count = await agent_call(cluster_items, batch_size)
    
    final_results = []
    if structured_data:
        for structure in structured_data:
            if isinstance(structure, str):
                extracted_json = extract_first_json_object(structure)
                if extracted_json:
                    final_results.append(extracted_json)
            else:
                final_results.append(structure)
    
    print(f"Cluster {cluster_id} processed: {len(final_results)} items, {cluster_token_count} tokens")
    return final_results, cluster_token_count


async def agent_recursion(clusters, batch_size=100): 
    """Process all clusters concurrently"""
    cluster_data = process_clusters(clusters)
    global_token_count = 0 
    
    # Create tasks for all clusters to run concurrently
    cluster_tasks = []
    for cluster_id, cluster_items in cluster_data.items():
        task = asyncio.create_task(
            process_single_cluster(cluster_id, cluster_items, batch_size)
        )
        cluster_tasks.append(task)
    
    # Run all cluster tasks concurrently
    print(f"Processing {len(cluster_tasks)} clusters concurrently...")
    cluster_results = await asyncio.gather(*cluster_tasks)
    
    # Aggregate all results
    final_results = []
    for cluster_final_results, cluster_token_count in cluster_results:
        final_results.extend(cluster_final_results)
        global_token_count += cluster_token_count
    
    print(f"Processed {len(final_results)} total items across all clusters")
    print(f"Total token usage across all clusters: {global_token_count}")          

    return final_results, global_token_count


# Main entry point to run the code
async def ppc_main(input_data, batch_size=100):
    """
    Main function with configurable batch size
    
    Args:
        input_data: Input data for processing
        batch_size: Batch size for processing (default: 100)
                   If > 100: batches within clusters run sequentially
                   If <= 100: batches within clusters run concurrently
                   Clusters always run concurrently regardless of batch size
    """
    results, total_token_count = await agent_recursion(input_data, batch_size)
    print(f"Total token count: {total_token_count}")
    return results, total_token_count


# Example usage
if __name__ == "__main__":
    # Example with different batch sizes
    csv_file = r"c:\Users\nickc\OneDrive\Desktop\SEO\ppc_process\data\PPC-test-source.xlsx"  
    df = pd.read_excel(csv_file)
    df1 = df[["Keyword"]]
    # Convert DataFrame to JSON
    data = df1.to_dict(orient="records")
    
    # Run with batch size > 100 (sequential batches within clusters, concurrent clusters)
    print("Running with batch size 150 (sequential batches)...")
    # asyncio.run(ppc_main(data, batch_size=150