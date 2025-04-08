import spacy
import os
import numpy as np
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
import traceback
from dotenv import load_dotenv

import asyncio
import json
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional

import json
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# from Prompt.prompt_content_generation import keyword_matching
from content_generation.Prompt.prompt_content_generation import keyword_matching
from content_generation.utils import clean_string
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
nlp = spacy.load("en_core_web_sm")
model_name = os.environ.get("OPENAI_MODEL")


def get_embeddings(text_list):
    """
    Generate embeddings for a list of texts using OpenAI API.
    """
   
    if not isinstance(text_list, list):
        raise ValueError("Input must be a list of strings")
    

    valid_texts = [clean_string(text) for text in text_list]
    valid_texts = [text for text in valid_texts if text is not None]
    
    if not valid_texts:
        print("No valid texts to process")
        return []
    
    try:
        response = client.embeddings.create(
            input=valid_texts, 
            model="text-embedding-ada-002"
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        print(f"Error in get_embeddings: {e}")
        traceback.print_exc()
        raise

def keywords_blog(keywords, text):
  
    cleaned_strings = [clean_string(s) for s in keywords]
    keyword_embeddings = get_embeddings(cleaned_strings)
    keyword_embeddings_matrix = np.array(keyword_embeddings)

    # doc = nlp(text)
    split_text = text.split('\n')
    sentences = [s.strip() for s in split_text if s.strip()]
    print(sentences)
    
    threshold = 0.75  
    results = []

    for sentence in sentences:
        sentence_doc = nlp(sentence)
     
        nouns = [token.text for token in sentence_doc if token.pos_ == "NOUN"]
        noun_phrases = [chunk.text for chunk in sentence_doc.noun_chunks]
        
        noun_matches = []
        noun_phrase_matches = []
        
  
        if nouns:
            noun_embeddings = get_embeddings(nouns)
            noun_embeddings_matrix = np.array(noun_embeddings)
            similarity_matrix = cosine_similarity(noun_embeddings_matrix, keyword_embeddings_matrix)
            
            for i, noun in enumerate(nouns):
                max_index = np.argmax(similarity_matrix[i])
                max_score = similarity_matrix[i, max_index]
                best_keyword = keywords[max_index]
                if max_score > threshold:
                    noun_matches.append({
                        "noun": noun,
                        "keyword": best_keyword,
                        "similarity": float(max_score)
                    })
        

        if noun_phrases:
            noun_phrase_embeddings = get_embeddings(noun_phrases)
            noun_phrase_embeddings_matrix = np.array(noun_phrase_embeddings)
            similarity_matrix_np = cosine_similarity(noun_phrase_embeddings_matrix, keyword_embeddings_matrix)
            
            for i, phrase in enumerate(noun_phrases):
                max_index = np.argmax(similarity_matrix_np[i])
                max_score = similarity_matrix_np[i, max_index]
                best_keyword = keywords[max_index]
                if max_score > threshold:
                    noun_phrase_matches.append({
                        "noun_phrase": phrase,
                        "keyword": best_keyword,
                        "similarity": float(max_score)
                    })
        
        results.append({
            "sentence": sentence,
            "noun_matches": noun_matches,
            "noun_phrase_matches": noun_phrase_matches
        })
    
    return results







async def open_ai_async(blog: str, sentence_data: Dict[str, Any], retry_count: int = 2) -> str:
    """
    Asynchronous version of open_ai function with error handling and retries.
    
    Args:
        blog: The full blog text
        sentence_data: Dict with 'sentence', 'noun_matches', and 'noun_phrase_matches'
        retry_count: Number of retry attempts for API failures
    
    Returns:
        Rewritten sentence or original sentence if all retries fail
    """
    original_sentence = sentence_data['sentence']
    query = ""
    
    try:
        replacements = (
            [{'original': m['noun'], 'keyword': m['keyword'], 'similarity': m['similarity']} 
            for m in sentence_data.get('noun_matches', [])] +
            [{'original': m['noun_phrase'], 'keyword': m['keyword'], 'similarity': m['similarity']} 
            for m in sentence_data.get('noun_phrase_matches', [])]
        )
        
      
        if not replacements:
            return original_sentence
            
        replacements_str = json.dumps(replacements, indent=2)
        
        formatted_prompt = keyword_matching.format(
            sentence=original_sentence,
            replacements=replacements_str,
            blog=blog
        )
        
        messages = [
            {'role': 'system', 'content': formatted_prompt},
            {'role': 'user', 'content': query}
        ]

        # Implement retry logic
        attempts = 0
        while attempts <= retry_count:
            try:
                # Run the API call in a thread to avoid blocking the event loop
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    response = await loop.run_in_executor(
                        executor,
                        lambda: client.chat.completions.create(
                            model=model_name,
                            messages=messages,
                            temperature=0.2
                        )
                    )

                full_response = response.choices[0].message.content.strip()
                final_sentence = full_response.split("Final Sentence:")[-1].strip()
                
           
                if not final_sentence:
                    raise ValueError("Empty response received from API")
                    
                return final_sentence
                
            except Exception as attempt_error:
                attempts += 1
                error_msg = f"Error in open_ai_async (attempt {attempts}/{retry_count+1}): {str(attempt_error)}"
                print(error_msg)
                
                if attempts <= retry_count:
                    # Wait with exponential backoff before retrying
                    backoff_time = 2 ** attempts
                    print(f"Retrying in {backoff_time} seconds...")
                    await asyncio.sleep(backoff_time)
                else:
                    print(f"All retry attempts failed for sentence: {original_sentence[:50]}...")
                    return original_sentence
    
    except Exception as e:
        error_msg = f"Unexpected error processing sentence: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        return original_sentence

async def process_sentence_batch(blog: str, batch: List[Dict[str, Any]], 
                               semaphore: asyncio.Semaphore) -> List[str]:
    """
    Process a batch of sentences with rate limiting via semaphore.
    
    Args:
        blog: The full blog text
        batch: List of sentence data dicts
        semaphore: Semaphore for rate limiting
    
    Returns:
        List of rewritten sentences
    """
    tasks = []
    for sentence_data in batch:
   
        async with semaphore:
            task = asyncio.create_task(open_ai_async(blog, sentence_data))
            tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle any exceptions that were returned
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Task failed with error: {str(result)}")
            # Fall back to original sentence
            processed_results.append(batch[i]['sentence'])
        else:
            processed_results.append(result)
    
    return processed_results

async def generation_blog_async(keywords: List[str], text: str, 
                              max_concurrent: int = 5) -> str:
    """
    Generate a rewritten blog by processing sentences concurrently with proper error handling.
    
    Args:
        keywords: List of keywords for content optimization
        text: Original blog text
        max_concurrent: Maximum number of concurrent API calls
    
    Returns:
        Rewritten blog text
    """
    try:
        # Get keyword data
        keywords_data = keywords_blog(keywords=keywords, text=text)
        
        if not keywords_data:
            print("No sentence data returned from keywords_blog. Returning original text.")
            return text
        
        # Create a semaphore to limit concurrent API calls
        semaphore = asyncio.Semaphore(max_concurrent)
        
        rewritten_sentences = await process_sentence_batch(text, keywords_data, semaphore)
        
        # Join all rewritten sentences with newlines
        blog_text = "\n".join(rewritten_sentences)
        
        return blog_text
        
    except Exception as e:
        error_msg = f"Error in generation_blog_async: {str(e)}"
        print(error_msg)
        traceback.print_exc()
  
        return text

# def generation_blog(keywords: List[str], text: str, max_concurrent: int = 5) -> str:
#     """
#     Non-async wrapper for the async function, with error handling
    
#     Args:
#         keywords: List of keywords for content optimization
#         text: Original blog text
#         max_concurrent: Maximum number of concurrent API calls
    
#     Returns:
#         Rewritten blog text or original text in case of failure
#     """
#     try:
#         return asyncio.run(generation_blog_async(keywords, text, max_concurrent))
#     except Exception as e:
#         error_msg = f"Critical error in generation_blog: {str(e)}"
#         print(error_msg)
#         traceback.print_exc()
#         return text