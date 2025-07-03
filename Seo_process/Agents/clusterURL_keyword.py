import sys
import os
import json
import asyncio
from openai import AsyncOpenAI
from openai import OpenAI
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from clustering_pipeline.k_mean import ClusteringConfig, Cluster 
from Seo_process.prompts.cluster_URL_prompt import prompt  
from utils import extract_first_json_object  
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

# Using AsyncOpenAI for better concurrency support
client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
model_name = os.environ.get("OPENAI_MODEL_2")
min_clusters = os.environ.get("MIN_CLUSTER")
max_clusters = os.environ.get("MAX_CLUSTER")


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

        response = await client.chat.completions.create(
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
        return None, None, None, 0


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


async def agent_call_sequential(cluster_items, batch_size=100):
    """Process batches sequentially for large batch sizes"""
    previous_page_titles = []
    structured_results = []
    previous_structured_URL = []
    total_token_count = 0

    # Create batches
    batches = [cluster_items[i:i+batch_size] for i in range(0, len(cluster_items), batch_size)]
    
    # Process batches sequentially to maintain context flow
    for i, batch in enumerate(batches):
        print(f"Processing batch {i+1}/{len(batches)} sequentially with {len(batch)} items")
        
        structured_data, batch_page_titles, url_structure, batch_tokens = await url_agent(
            PROMPT=prompt,
            items=batch, 
            previous_page_titles=previous_page_titles,
            previous_URL=previous_structured_URL
        )
        
        if batch_tokens:
            total_token_count += batch_tokens
            print(f"Batch token count: {batch_tokens}, Running total: {total_token_count}")

        if structured_data:
            structured_results.extend([structured_data] if not isinstance(structured_data, list) else structured_data)

        if batch_page_titles:
            previous_page_titles.extend(batch_page_titles)  

        if url_structure:
            previous_structured_URL.extend(url_structure) 

    print(f"Processed {len(structured_results)} items sequentially")
    return structured_results, total_token_count


async def agent_call_concurrent(cluster_items, batch_size=100):
    """Process batches concurrently for smaller batch sizes"""
    # Note: For SEO processing, we might still want sequential processing 
    # to maintain context between batches. But implementing concurrent for completeness.
    structured_results = []
    total_token_count = 0

    # Create batches
    batches = [cluster_items[i:i+batch_size] for i in range(0, len(cluster_items), batch_size)]
    tasks = []

    # Create tasks for all batches (without previous context sharing)
    for i, batch in enumerate(batches):
        print(f"Creating concurrent task for batch {i+1} with {len(batch)} items")
        task = asyncio.create_task(url_agent(
            PROMPT=prompt,
            items=batch, 
            previous_page_titles=[],  # Empty for concurrent processing
            previous_URL=[]  # Empty for concurrent processing
        ))
        tasks.append(task)

    # Run all tasks concurrently
    results = await asyncio.gather(*tasks)

    # Aggregate results
    for structured_data, batch_page_titles, url_structure, batch_tokens in results:
        if batch_tokens:
            total_token_count += batch_tokens
            print(f"Batch token count: {batch_tokens}, Running total: {total_token_count}")

        if structured_data:
            structured_results.extend([structured_data] if not isinstance(structured_data, list) else structured_data)

    print(f"Processed {len(structured_results)} items concurrently")
    return structured_results, total_token_count


async def agent_call(cluster_items, batch_size=100):
    """Main function to decide between sequential or concurrent processing"""
    if batch_size > 100:
        print(f"Batch size {batch_size} > 100, processing sequentially")
        return await agent_call_sequential(cluster_items, batch_size)
    else:
        print(f"Batch size {batch_size} <= 100, processing concurrently")
        # For SEO, you might want to use sequential even for smaller batches
        # to maintain context. Uncomment the line below if needed:
        # return await agent_call_sequential(cluster_items, batch_size)
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
                # Already a dict/JSON object
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
async def seo_main(input_data, batch_size=100, maintain_context=True):
    """
    Main function with configurable batch size and context handling
    
    Args:
        input_data: Input data for processing
        batch_size: Batch size for processing (default: 100)
                   If > 100: batches within clusters run sequentially
                   If <= 100: batches within clusters run concurrently (or sequentially if maintain_context=True)
                   Clusters always run concurrently regardless of batch size
        maintain_context: If True, always use sequential processing to maintain context between batches
    """
    if maintain_context:
        print("Context maintenance enabled - using sequential processing for all batches")
        # Override the concurrent logic for SEO context preservation
        original_agent_call = globals()['agent_call']
        
        async def context_preserving_agent_call(cluster_items, batch_size=100):
            return await agent_call_sequential(cluster_items, batch_size)
        
        globals()['agent_call'] = context_preserving_agent_call
    
    results, total_token_count = await agent_recursion(input_data, batch_size)
    print(f"Total token count: {total_token_count}")
    return results, total_token_count


# Example usage
# if __name__ == "__main__":
    # # Example with different batch sizes and context options
    # csv_file = r"C:\Users\nickc\Downloads\dhs kwr test.csv"  # Replace with your file path
    # df = pd.read_csv(csv_file)
    # df1 = df[["Keyword"]]
    # # Convert DataFrame to JSON
    # data = df1.to_dict(orient="records")
    
    # # Option 1: Sequential batches with context preservation (recommended for SEO)
    # print("Running with batch size 150 and context preservation...")
    # # asyncio.run(seo_main(data, batch_size=150, maintain_context=True))
    
    # # Option 2: Concurrent batches without context (faster but may lose context)
    # print("Running with batch size 50 concurrent batches...")
    # # asyncio.run(seo_main(data, batch_size=50, maintain_context=False))
    
    # # Option 3: Default behavior (batch_size=100, with context)
    # # asyncio.run(seo_main(data))