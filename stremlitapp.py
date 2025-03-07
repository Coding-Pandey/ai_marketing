import streamlit as st
import requests
import pandas as pd
import json
from io import BytesIO
# FastAPI backend URLs
GENERATE_API_URL = "http://127.0.0.1:8000/seo_generate_keywords"
SUGGEST_API_URL = "http://127.0.0.1:8000/seo_keyword_suggestion"
CLUSTER_API_URL = "http://127.0.0.1:8000/seo_keyword_clustering"

# Streamlit UI
st.title("SEO Keyword Generator & Suggestion Tool")

# User Input
keywords = st.text_input("Enter Keywords (comma-separated):", placeholder="e.g., SEO, Machine Learning, Automation")
description = st.text_area("Enter a Short Description (Optional):", placeholder="Describe your business or service")

# Session state to store DataFrames
if "df" not in st.session_state:
    st.session_state.df = None
if "processed_df" not in st.session_state:
    st.session_state.processed_df = None

# Function to fetch keywords from API
def fetch_keywords(api_url):
    if not keywords and not description:
        st.error("Please provide at least one input (keywords or description).")
        return

    payload = {"keywords": keywords, "description": description}
    response = requests.post(api_url, json=payload)

    if response.status_code == 200:
        data = response.json()
        st.success("Keywords Generated Successfully!")

        # Display extracted keywords as JSON
        st.subheader("Extracted Keywords:")
        st.json(data)

        # Convert JSON list to DataFrame
        try: 
            keywords_list = json.loads(data) if isinstance(data, str) else data
            if isinstance(keywords_list, list) and all(isinstance(item, dict) for item in keywords_list):
                df = pd.DataFrame(keywords_list)
                st.session_state.df = df
            else:
                st.error("Unexpected JSON format received!")
        except json.JSONDecodeError:
            st.error("Failed to parse JSON response!")
    else:
        st.error(f"Error: {response.json().get('detail', 'Unknown error')}")

# Function to fetch additional suggested keywords
def fetch_suggested_keywords():
    if not keywords:
        st.error("Please provide some keywords for suggestions.")
        return

    payload = {"keywords": keywords, "description": description}
    response = requests.post(SUGGEST_API_URL, json=payload)
    
    if response.status_code == 200:
        suggested_keywords = response.json()
        st.success("Suggested Keywords Generated!")

        st.write(suggested_keywords)
    else:
        st.error(f"Error: {response.json().get('detail', 'Unknown error')}")

# Function to process keywords using the clustering API (upload file)
def process_keywords():
    if st.session_state.df is None or st.session_state.df.empty:
        st.error("No data available to process.")
        return

    # Convert DataFrame to CSV (in-memory)
    csv_buffer = BytesIO()
    st.session_state.df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    # Send CSV file to FastAPI
    files = {"file": ("keywords.csv", csv_buffer, "text/csv")}
    response = requests.post(CLUSTER_API_URL, files=files)

    if response.status_code == 200:
        st.success("Keywords Processed Successfully!")
        processed_data = response.json()

        # Convert JSON response to DataFrame
        try:
            processed_df = pd.DataFrame(processed_data)
            st.session_state.processed_df = processed_df
            st.subheader("Processed Keywords DataFrame:")
            st.dataframe(processed_df)
        except Exception as e:
            st.error(f"Error converting processed data to DataFrame: {e}")
    else:
        st.error(f"Error: {response.json().get('detail', 'Unknown error')}")

# Buttons for generating and suggesting keywords
col1, col2 = st.columns(2)
with col1:
    if st.button("Generate Keywords"):
        fetch_keywords(GENERATE_API_URL)
        
with col2:
    if st.button("Suggest More Keywords"):
        fetch_suggested_keywords()

# Show DataFrame if available
if st.session_state.df is not None:
    st.subheader("Editable Keywords DataFrame:")

    # Add a checkbox column for deletion
    df = st.session_state.df.copy()
    df["Delete"] = False  # Default unchecked
    edited_df = st.data_editor(df, key="data_editor", num_rows="dynamic", use_container_width=True)

    # Handle row deletion
    if st.button("Delete Selected Rows"):
        st.session_state.df = edited_df[edited_df["Delete"] == False].drop(columns=["Delete"])
        st.success("Selected rows deleted!")

    # Save updated DataFrame
    if st.button("Save"):
        st.session_state.df = edited_df.drop(columns=["Delete"])
        st.success("Changes Saved!")


    # Download the modified DataFrame as CSV
    if st.session_state.df is not None and not st.session_state.df.empty:
        csv = st.session_state.df.to_csv(index=False)
        st.download_button(label="Download CSV", data=csv, file_name="keywords.csv", mime="text/csv")

    # Move "Clear DataFrame" button to the end
    if st.button("Clear DataFrame"):
        st.session_state.df = None
        st.session_state.processed_df = None
        st.success("Data Cleared!")

    # Process keywords (send to clustering API)
    if st.button("Process Keywords"):
        process_keywords()

        
# Show Processed Keywords DataFrame if available
if st.session_state.processed_df is not None:
    st.subheader("Processed Keywords DataFrame:")
    st.dataframe(st.session_state.processed_df)
