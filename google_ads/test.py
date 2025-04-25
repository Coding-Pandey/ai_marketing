from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.oauth2 import service_account
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_client():
    """Create and return a Google Ads API client using service account credentials."""
    # Get the path to the service account JSON key file
    SERVICE_ACCOUNT_FILE = r"C:\Users\Administrator\Downloads\optiminder-app-ddb4835450d4.json"

    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise ValueError(f"Service account file not found at: {SERVICE_ACCOUNT_FILE}")
    
    # Load credentials from the service account file
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/adwords']
    )
    
    # Developer token - in production, this should be in env variables
    DEVELOPER_TOKEN = "WZB9Nw_22F8kW6PQh8bUpg"
    
    # Retrieve the customer ID from an environment variable
    CUSTOMER_ID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID")
    if not CUSTOMER_ID:
        raise ValueError("Customer ID must be set in environment variable GOOGLE_ADS_CUSTOMER_ID")
    
    # Initialize and return the GoogleAdsClient
    return GoogleAdsClient(
        credentials=credentials,
        developer_token=DEVELOPER_TOKEN,
        use_proto_plus=True,
        login_customer_id=CUSTOMER_ID
    )

def get_language_resource_name(client, customer_id, language_id):
    """Fetch the resource name of a language constant using Google Ads API."""
    try:
        ga_service = client.get_service("GoogleAdsService")
        
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
        
        # Create keyword plan idea request
        request = client.get_type("GenerateKeywordIdeasRequest")
        request.customer_id = customer_id
        request.language = f"languageConstants/{language_id}"
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
            metrics = idea.keyword_idea_metrics
            data.append({
                "Keyword": idea.text,
                "Avg_Monthly_Searches": metrics.avg_monthly_searches if metrics else 0
            })
        
        return data
        
    except GoogleAdsException as ex:
        print(f"❌ Google Ads API Error: {ex}")
        for error in ex.failure.errors:
            print(f"\tError code: {error.error_code}")
            print(f"\tError message: {error.message}")
        return None

def seo_keywords_main(keywords, location_ids=None, language_id=None):
    """Main function to get keyword ideas."""
    try:
        # Load client
        client = get_client()
        
        # Set default values if not provided
        if location_ids is None:
            # 2826 is for United States
            location_ids = [2826]
        
        if language_id is None:
            # 1000 is for English
            language_id = 1000
        
        customer_id = os.environ.get("GOOGLE_ADS_CUSTOMER_ID")
        if not customer_id:
            raise ValueError("Customer ID not set in environment variables")
        
        # Generate keyword ideas
        result = generate_keyword_ideas(
            client=client,
            customer_id=customer_id,
            location_ids=location_ids,
            language_id=language_id,
            keywords=keywords
        )
        
        return result
    
    except Exception as e:
        print(f"❌ Error in main function: {e}")
        return None

if __name__ == "__main__":
    keywords = ["eis investment"]
    result = seo_keywords_main(keywords=keywords)
    
    # Print results in a readable format
    if result:
        print(f"Found {len(result)} keyword ideas:")
        for idx, keyword_data in enumerate(result, 1):
            print(f"\n{idx}. {keyword_data['Keyword']}")
            print(f"   Monthly Searches: {keyword_data['Avg_Monthly_Searches']}")
    else:
        print("No keyword ideas found or an error occurred.")