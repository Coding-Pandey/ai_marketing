from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from google_ads.clinet import get_client
from dotenv import load_dotenv
load_dotenv()

def get_currency_for_location(client, customer_id, location_id):
    """Fetches the currency used in a given location from Google Ads API."""
    try:
        ga_service = client.get_service("GoogleAdsService")

        query = f"""
            SELECT geo_target_constant.resource_name, geo_target_constant.id, 
                   geo_target_constant.name, geo_target_constant.currency_code
            FROM geo_target_constant
            WHERE geo_target_constant.id = {location_id}
        """

        response = ga_service.search(customer_id=customer_id, query=query)
        
        for row in response:
            return row.geo_target_constant.currency_code  # Return currency (e.g., GBP, EUR, USD)

        # return "USD"  # Default to USD if not found

    except GoogleAdsException as ex:
        print(f"❌ Error fetching currency for location {location_id}: {ex}")
        return None # Fallback to USD
    

def generate_keyword_ideas(client, customer_id, location_ids, language_id, keywords):
    """Fetch keyword ideas from Google Ads API."""
    try:
        keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")

        # Create the request
        request = client.get_type("GenerateKeywordIdeasRequest")
        request.customer_id = customer_id
        
        # Set the seed keywords
        request.keyword_seed.keywords.extend(keywords)
        
        # Set language and location
        request.language = f"languageConstants/{language_id}"
        
        for location_id in location_ids:
            request.geo_target_constants.append(f"geoTargetConstants/{location_id}")
        
        # currency = get_currency_for_location(client, customer_id, location_ids[0])
        # Execute the request
        response = keyword_plan_idea_service.generate_keyword_ideas(request=request)

        # Process and store the results
        keyword_suggestions = []
        for idea in response:
            metrics = idea.keyword_idea_metrics
            keyword_data = {
                "Keyword": idea.text,
                "Avg Monthly Searches": metrics.avg_monthly_searches if metrics else 0,
                "Competition": metrics.competition.name if metrics and metrics.competition else "UNKNOWN",
                "LowTopOfPageBid": metrics.low_top_of_page_bid_micros / 1_000_000 if metrics and metrics.low_top_of_page_bid_micros else 0.0,
                "HighTopOfPageBid": metrics.high_top_of_page_bid_micros / 1_000_000 if metrics and metrics.high_top_of_page_bid_micros else 0.0
                # "Currency": currency
            }
            keyword_suggestions.append(keyword_data)

        return keyword_suggestions    
            
    except GoogleAdsException as ex:
        print(f"❌ Google Ads API Error: {ex}")
        for error in ex.failure.errors:
            print(f"\tError code: {error.error_code}")
            print(f"\tError message: {error.message}")
        return None

def ppc_keywords_main(keywords, location_ids=None, language_id=None):
    """Main function to retrieve keyword ideas using Google Ads API."""
    try:
        # Load client from YAML config file
        client = get_client()
    except Exception as e:
        print(f"❌ Error loading client configuration: {e}")
        return
    
    if location_ids is None:
        location_ids = [2840]  # Default: United States
    if language_id is None:     
        language_id = "1000"  # Default: English
    customer_id = os.environ.get("GOOGLE_ADS_CUSTOMER_ID") 
    
    # Generate keyword ideas
    result = generate_keyword_ideas(
        client=client,
        customer_id=customer_id,
        location_ids=location_ids,
        language_id=language_id,
        keywords=keywords
    )

    return result

if __name__ == "__main__":
   
    seed_keywords = ["ai agent"]
    location_ids = ["2840"] 
    language_id = "1000"  


    suggestions = ppc_keywords_main(seed_keywords, location_ids, language_id)

    # Print results
    if suggestions:
        print(suggestions)
    else:
        print("❌ No keyword suggestions found.")
