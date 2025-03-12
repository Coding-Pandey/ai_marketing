from google.ads.googleads.client import GoogleAdsClient


def get_client():
    try:
        client = GoogleAdsClient.load_from_storage(
            r"C:\Users\nickc\OneDrive\Desktop\AI marketing\google_ads\google-ads.yaml"
        )
        # client = GoogleAdsClient.load_from_storage(
        #     "/home/ubuntu/ai_marketing/google_ads/google-ads.yaml",
        #     version="v18"
        # )
        return client
    except Exception as e:
        print(f"Error in get_client: {e}")
        return None
