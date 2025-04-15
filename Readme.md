# AI Marketing API Documentation

## 1st Endpoint: `/seo_generate_keywords`

### Overview
This endpoint generates SEO keywords based on user input and retrieves search metrics from the Google Ads API. It supports filtering keywords by various criteria, including branded terms and search volume thresholds.

### HTTP Method
`POST`

### Request Parameters
The endpoint accepts a JSON object with the following fields:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `keywords` | string | Optional | Keywords to use as a basis for generating additional related keywords |
| `description` | string | Optional | Description text to analyze for keyword extraction |
| `exclude_values` | array of integers | Optional | Threshold values for filtering keywords by search volume |
| `branded_keyword` | array of strings | Optional | List of branded terms to filter out from results |
| `location_ids` | array of integers | Required* | Geographic location IDs for search volume targeting |
| `language_id` | integer | Required* | Language ID for keyword search metrics |
| `branded_words` | boolean | Optional | Flag to filter non-branded keywords when set to true |

\* Either `location_ids` or `language_id` must be provided.

### Response Format
Returns an array of objects, each containing:

```json
{
  "Keyword": "example keyword phrase",
  "Avg Monthly Searches": 1200
}
```

### Example Request
```json
{
  "keywords": "digital marketing services",
  "description": "Professional SEO and content marketing services for small businesses",
  "exclude_values": [10, 50],
  "branded_keyword": ["acme", "company name"],
  "location_ids": [2840],
  "language_id": 1000,
  "branded_words": true
}
```

### Error Responses

| Status Code | Description |
|-------------|-------------|
| 400 | Invalid request parameters or both location and language missing |
| 500 | Failed to fetch keyword data from Google Ads API |

### Process Flow
1. Validates input parameters
2. Checks that either location_ids or language_id is provided
3. Generates keywords from input text using AI prompt
4. Queries Google Ads API for keyword metrics
5. Applies filters (if specified):
   - Removes keywords below specified search volumes
   - Filters non-branded keywords if requested
   - Removes branded keywords from results
6. Returns the filtered list of keywords with their search volumes

### Notes
- The endpoint stores branded keywords in a JSON file for future reference
- Error handling is implemented for API failures and invalid inputs
- Keyword extraction leverages an AI model via the `query_keywords_description` function



---------------------------------------------------------------------------------------------------

## 2nd Endpoint: `/seo_keyword_suggestion`

### Overview
This endpoint provides keyword suggestions for SEO optimization based on user input keywords and/or description text. It uses an AI model to generate relevant keyword suggestions that can improve search engine visibility.

### HTTP Method
`POST`

### Request Parameters
The endpoint accepts a JSON object with the following fields:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `keywords` | string | Optional* | Seed keywords to generate suggestions from |
| `description` | string | Optional* | Description text to analyze for keyword suggestions |

\* At least one of `keywords` or `description` must be provided.

### Response Format
Returns a JSON object containing suggested keywords. The exact structure depends on the AI model's response format, but typically includes categorized keyword suggestions.

### Example Request
```json
{
  "keywords": "organic skincare products",
  "description": "Natural and eco-friendly skincare solutions made with organic ingredients"
}
```

### Example Response
```json
{
  "keywords": [
    "organic skincare products",
    "natural skincare solutions",
    "eco-friendly skincare"
 ]
}
```

### Error Responses

| Status Code | Error Code | Description | Possible Resolution |
|-------------|------------|-------------|---------------------|
| 400 | INVALID_PARAMETERS | Invalid request parameters | Verify the request body follows the required schema |
| 400 | MISSING_REQUIRED_FIELDS | Neither keywords nor description provided | Provide at least one of keywords or description |
| 500 | AI_MODEL_ERROR | Error in processing with AI model | Try again later or with different input |
| 500 | INTERNAL_SERVER_ERROR | Unexpected server error | Contact API support with error details |

### Process Flow
1. Validates input parameters (requires at least one of keywords or description)
2. Sends the input to an AI model for keyword suggestion processing
3. Returns the suggested keywords in JSON format

### Notes
- The quality of suggestions depends on the specificity and relevance of the input provided
- The API uses an AI model to generate contextually relevant keyword suggestions
- Processing time may vary based on input complexity and server load


-------------------------------------------------------------------------------------

## 3rd Endpoint: `/seo_keyword_clustering`

### Overview
This endpoint processes uploaded keyword data and performs semantic clustering to group related keywords. It helps optimize SEO strategy by organizing keywords into logical groups based on search intent and relevance.

### HTTP Method
`POST`

### Request Format
This endpoint accepts a file upload using multipart/form-data.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | File | Required | CSV file containing keyword data with at least a "Keyword" column and optionally "Avg Monthly Searches" |

### Response Format
Returns a JSON array of clustered keyword objects, each containing:

```json
{
  "keyword": "example keyword phrase",
  "avg_monthly_searches": 1200
}
```

### Example Response
```json
[
  {
    "page_title": "Organic Skincare Benefits",
    "keyword": "organic skincare benefits",
    "intent": "informational",
    "url_structure": "/organic-skincare-benefits",
    "avg_monthly_searches": 1200
  },
  {
    "page_title": "Organic Skincare Benefits",
    "keyword": "benefits of natural skincare products",
    "intent": "informational",
    "url_structure": "/organic-skincare-benefits",
    "avg_monthly_searches": 880
  },
  {
    "page_title": "Best Organic Face Creams",
    "keyword": "best organic face cream",
    "intent": "commercial",
    "url_structure": "/best-organic-face-creams",
    "avg_monthly_searches": 2400
  }
]
```

### Error Responses

| Status Code | Error Code | Description | Possible Resolution |
|-------------|------------|-------------|---------------------|
| 400 | NO_FILE_UPLOADED | No file provided in request | Include a CSV file in the request |
| 400 | INVALID_FILE_FORMAT | File format is not valid | Upload a proper CSV file with required columns |
| 400 | MISSING_REQUIRED_COLUMNS | CSV file is missing the "Keyword" column | Ensure CSV contains a "Keyword" column |
| 500 | CLUSTERING_ERROR | Error in the clustering algorithm | Try with a smaller dataset or contact support |
| 500 | INTERNAL_SERVER_ERROR | Unexpected server error | Contact API support with error details |

### Process Flow
1. Uploads and parses CSV file containing keyword data
2. Extracts the "Keyword" column for clustering analysis
3. Processes keywords through semantic clustering algorithm
4. Maps additional data (like search volumes) from the original dataset
5. Returns organized keyword clusters with page titles, intent classification, and suggested URL structures

### Notes
- The CSV file must contain at least a "Keyword" column
- For best results, include "Avg Monthly Searches" data for each keyword
- Processing time depends on the number of keywords (larger datasets will take longer)
- The clustering algorithm uses semantic analysis to group similar keywords by topic and search intent
- URL structures are automatically generated based on the clustered topics

-----------------------------------------------------------------------------------


## 4th Endpoint: `/ppc_generate_keywords`

### Overview
This endpoint generates Pay-Per-Click (PPC) advertising keywords based on user input and retrieves comprehensive metrics from the Google Ads API, including competition and bid pricing information.

### HTTP Method
`POST`

### Request Parameters
The endpoint accepts a JSON object with the following fields:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `keywords` | string | Optional* | Seed keywords to generate PPC suggestions from |
| `description` | string | Optional* | Description text to analyze for keyword extraction |
| `exclude_values` | array of integers | Optional | Threshold values for filtering keywords by search volume |
| `branded_keyword` | array of strings | Optional | List of branded terms to filter out from results |
| `location_ids` | array of integers | Required | Geographic location IDs for search volume targeting |
| `language_id` | integer | Required | Language ID for keyword search metrics |
| `branded_words` | boolean | Optional | Flag to filter non-branded keywords when set to true |

\* At least one of `keywords` or `description` must be provided.

### Response Format
Returns an array of objects, each containing:

```json
{
  "Keyword": "example keyword phrase",
  "Avg Monthly Searches": 1200,
  "Competition": "HIGH",
  "LowTopOfPageBid": 0.75,
  "HighTopOfPageBid": 1.25
}
```

### Example Request
```json
{
  "keywords": "running shoes",
  "description": "High performance athletic footwear for marathon runners",
  "exclude_values": [100, 500],
  "branded_keyword": ["nike", "adidas"],
  "location_ids": [2840],
  "language_id": 1000,
  "branded_words": false
}
```

### Error Responses

| Status Code | Error Code | Description | Possible Resolution |
|-------------|------------|-------------|---------------------|
| 400 | INVALID_PARAMETERS | Invalid request parameters | Verify the request body follows the required schema |
| 400 | MISSING_REQUIRED_FIELDS | Neither keywords nor description provided | Provide at least one of keywords or description |
| 400 | MISSING_LOCATION_AND_LANGUAGE | Both location_ids and language_id are missing | Provide both location_ids and language_id |
| 400 | INVALID_KEYWORDS | Failed to extract or process keywords | Ensure keywords or description contains valid content |
| 500 | GOOGLE_ADS_API_ERROR | Failed to fetch keyword data from Google Ads API | Check API credentials and try again later |
| 500 | INVALID_API_RESPONSE | Invalid response from Google Ads API | Check API service status and try again later |

### Process Flow
1. Validates input parameters, ensuring at least one of keywords or description is provided
2. Verifies that both location_ids and language_id are specified
3. Generates keywords from input text using AI prompt
4. Queries Google Ads API for keyword metrics including:
   - Average monthly searches
   - Competition level (LOW, MEDIUM, HIGH)
   - Low and high top-of-page bid estimates
5. Applies filters (if specified):
   - Removes keywords below specified search volumes
   - Filters non-branded keywords if requested
   - Removes branded keywords from results
6. Returns the filtered list of keywords with their PPC metrics

### Notes
- Competition values are returned as text categories: "LOW", "MEDIUM", "HIGH", or "UNKNOWN"
- Bid values are in the account's currency and represent cost-per-click (CPC)
- Search volume metrics are averaged over the last 12 months
- Location and language IDs must match valid Google Ads API identifiers

-----------------------------------------------------------------------


## 5th Endpoint: `/ppc_keyword_clustering`

### Overview
This endpoint processes uploaded PPC keyword data and performs semantic clustering to organize keywords into logical ad groups. It also generates recommended ad headlines and descriptions for each group, optimizing your PPC campaign structure.

### HTTP Method
`POST`

### Request Format
This endpoint accepts a file upload using multipart/form-data.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | File | Required | CSV file containing PPC keyword data with at least a "Keyword" column and optionally other metrics columns |

### Required CSV File Format
The CSV file should contain at least the following columns:
- "Keyword" (required)
- "Avg Monthly Searches" (optional)
- "Competition" (optional)
- "LowTopOfPageBid" (optional)
- "HighTopOfPageBid" (optional)

### Response Format
Returns a JSON array of clustered keyword objects organized by ad groups, including suggested ad copy, with each object containing:

```json
{
  "Ad Group": "Running Shoes Premium",
  "Keywords": "marathon running shoes",
  "Avg. Monthly Searches": 2500,
  "Top of Page Bid Low": 1.25,
  "Top of Page Bid High": 2.75,
  "Ad Headline": "Premium Marathon Running Shoes | Performance Footwear",
  "Description": "Find the perfect running shoes for your next marathon. Engineered for comfort and speed."
}
```

### Example Response
```json
[
  {
    "Ad Group": "Running Shoes Premium",
    "Keywords": "marathon running shoes",
    "Avg. Monthly Searches": 2500,
    "Top of Page Bid Low": 1.25,
    "Top of Page Bid High": 2.75,
    "Ad Headline": "Premium Marathon Running Shoes | Performance Footwear",
    "Description": "Find the perfect running shoes for your next marathon. Engineered for comfort and speed."
  },
  {
    "Ad Group": "Running Shoes Premium",
    "Keywords": "professional running footwear",
    "Avg. Monthly Searches": 1800,
    "Top of Page Bid Low": 1.15,
    "Top of Page Bid High": 2.50,
    "Ad Headline": "Premium Marathon Running Shoes | Performance Footwear",
    "Description": "Find the perfect running shoes for your next marathon. Engineered for comfort and speed."
  },
  {
    "Ad Group": "Running Shoes Budget",
    "Keywords": "affordable running shoes",
    "Avg. Monthly Searches": 3200,
    "Top of Page Bid Low": 0.75,
    "Top of Page Bid High": 1.65,
    "Ad Headline": "Affordable Running Shoes | Quality Without The Price Tag",
    "Description": "High-quality running shoes that won't break the bank. Shop our collection today."
  }
]
```

### Error Responses

| Status Code | Error Description | Possible Resolution |
|-------------|-------------------|---------------------|
| 400 | "No file uploaded" | Include a CSV file in the request |
| 400 | "Invalid file format" | Upload a proper CSV file with required columns |
| 400 | "Missing required 'Keyword' column" | Ensure CSV contains a "Keyword" column |
| 500 | "Error processing file" | Check that your file is properly formatted and not corrupted |
| 500 | "Clustering algorithm error" | Try with a smaller dataset or contact support |

### Process Flow
1. Uploads and parses CSV file containing PPC keyword data
2. Extracts the "Keyword" column for clustering analysis
3. Processes keywords through semantic clustering algorithm to form logical ad groups
4. Maps additional metrics data (search volumes, bid prices) from the original dataset
5. Generates optimized ad headlines and descriptions for each ad group
6. Returns organized PPC campaign structure with keywords grouped by ad groups

### Notes
- The CSV file must contain at least a "Keyword" column
- For best results, include metrics data for each keyword
- Processing time depends on the number of keywords (larger datasets will take longer)
- The clustering algorithm uses semantic analysis to group similar keywords that will perform well together in the same ad group
- Ad copy suggestions are automatically generated based on the clustered topics and intent analysis
- The number of ad groups created will depend on the semantic diversity of your keywords


