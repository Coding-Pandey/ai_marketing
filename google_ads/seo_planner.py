from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

def get_language_resource_name(client, customer_id, language_id):
    """Fetch the resource name of a language constant using Google Ads API."""
    try:
        ga_service = client.get_service("GoogleAdsService")
        print(ga_service)

        query = f"""
            SELECT language_constant.resource_name 
            FROM language_constant 
            WHERE language_constant.id = {language_id}
        """

        response = ga_service.search(customer_id=customer_id, query=query)

        for row in response:
            return row.language_constant.resource_name  # Return the resource name

        raise ValueError(f"❌ Language ID {language_id} not found.")

    except GoogleAdsException as ex:
        for error in ex.failure.errors:
            print(f"\tError details: {error.message}")
        return None
    

def generate_keyword_ideas(client, customer_id, location_ids, language_id, keywords):
    """Fetch keyword ideas from Google Ads API."""
    try:
        keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")
        
        # Convert location IDs to resource names
        location_rns = [f"geoTargetConstants/{loc}" for loc in location_ids]
        
        # Get language resource name
        language_rn = get_language_resource_name(client, customer_id, language_id)
        if not language_rn:
            print("❌ Could not fetch language resource name. Exiting.")
            return
            
        # Create keyword plan idea request
        request = client.get_type("GenerateKeywordIdeasRequest")
        request.customer_id = customer_id
        request.language = language_rn
        request.geo_target_constants.extend(location_rns)
        
        # Set up keyword seed using extend to add each keyword from the list
        keyword_seed = client.get_type("KeywordSeed")
        keyword_seed.keywords.extend(keywords)
        request.keyword_seed = keyword_seed
        
        # Make the request
        keyword_ideas = keyword_plan_idea_service.generate_keyword_ideas(request=request)
        
        # Process results into a list of dictionaries
        data = []
        for idea in keyword_ideas:
            data.append({
                "Keyword": idea.text,
                "Avg Monthly Searches": idea.keyword_idea_metrics.avg_monthly_searches,
            })

        print(data)
        return data    
            
    except GoogleAdsException as ex:
        print(f"❌ Google Ads API Error: {ex}")
        for error in ex.failure.errors:
            print(f"\tError code: {error.error_code}")
            print(f"\tError message: {error.message}")
        return None

def seo_keywords_main(keywords, location_ids, language_id):
    # Load client from YAML config file
    try:
        client = GoogleAdsClient.load_from_storage(
            "/home/ubuntu/ai_marketing/google_ads/google-ads.yaml",
            version="v18"
        )

        # client = GoogleAdsClient.load_from_storage(
        #     r"C:\Users\nickc\OneDrive\Desktop\AI marketing\google_ads\google-ads.yaml",
        #     version="v18"
        # )
    except Exception as e:
        print(f"❌ Error loading client configuration: {e}")
        return
    
    if location_ids is None:
        location_ids = [2840] 
    if language_id is None:     
        language_id = 1036  
    customer_id = "6655930925"  
    # keywords = ["AI agent", "Database"]
    
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
    key = ["AI agent", "Database"]
    seo_keywords_main(keywords=key, location_ids=None, language_id=None)
