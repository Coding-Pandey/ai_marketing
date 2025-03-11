import streamlit as st
import requests
import pandas as pd
import json
from io import BytesIO
from typing import List, Optional

st.set_page_config(layout="wide")

# Streamlit UI
st.title("AI marketing tool")


# FastAPI backend URLs
GENERATE_API_URL = "http://127.0.0.1:8000/seo_generate_keywords"
SUGGEST_API_URL = "http://127.0.0.1:8000/seo_keyword_suggestion"
CLUSTER_API_URL = "http://127.0.0.1:8000/seo_keyword_clustering"

# Create tabs for SEO and PPC processes
tab1, tab2, tab3 = st.tabs(["SEO Process", "PPC Process", "Keywords suggestions"])

# Initialize session state for both tabs
if "seo_df" not in st.session_state:
    st.session_state.seo_df = None
if "seo_processed_df" not in st.session_state:
    st.session_state.seo_processed_df = None
if "ppc_df" not in st.session_state:
    st.session_state.ppc_df = None
if "ppc_processed_df" not in st.session_state:
    st.session_state.ppc_processed_df = None

# Sample location and language data (replace with your actual data)
location_options =[
    {"id": 2840, "country": "United States"},
    {"id": 2638, "country": "United Kingdom"},
    {"id": 2616, "country": "Poland"},
    {"id": 2276, "country": "Germany"},
    {"id": 2250, "country": "France"},
    {"id": 2380, "country": "Italy"},
    {"id": 2724, "country": "Spain"},
    {"id": 2124, "country": "Canada"},
    {"id": 2036, "country": "Australia"},
    {"id": 2356, "country": "India"},
    {"id": 2392, "country": "Japan"},
    {"id": 2484, "country": "China"},
    {"id": 2076, "country": "Brazil"},
    {"id": 2156, "country": "Mexico"},
    {"id": 2252, "country": "Russia"},
    {"id": 2190, "country": "South Africa"}
]

language_options = [
    {
        "ID": 1000,
        "Name": "English"
    },
    {
        "ID": 1001,
        "Name": "German"
    },
    {
        "ID": 1002,
        "Name": "French"
    },
    {
        "ID": 1003,
        "Name": "Spanish"
    },
    {
        "ID": 1004,
        "Name": "Italian"
    },
    {
        "ID": 1005,
        "Name": "Japanese"
    },
    {
        "ID": 1006,
        "Name": "English (US)"
    },
    {
        "ID": 1007,
        "Name": "English (UK)"
    },
    {
        "ID": 1008,
        "Name": "Chinese"
    },
    {
        "ID": 1009,
        "Name": "Danish"
    },
    {
        "ID": 1010,
        "Name": "Dutch"
    },
    {
        "ID": 1011,
        "Name": "Finnish"
    },
    {
        "ID": 1012,
        "Name": "Korean"
    },
    {
        "ID": 1013,
        "Name": "Norwegian"
    },
    {
        "ID": 1014,
        "Name": "Portuguese"
    },
    {
        "ID": 1015,
        "Name": "Swedish"
    },
    {
        "ID": 1016,
        "Name": "Portuguese (Brazil)"
    },
    {
        "ID": 1017,
        "Name": "Chinese (simplified)"
    },
    {
        "ID": 1018,
        "Name": "Chinese (traditional)"
    },
    {
        "ID": 1019,
        "Name": "Arabic"
    },
    {
        "ID": 1020,
        "Name": "Bulgarian"
    },
    {
        "ID": 1021,
        "Name": "Czech"
    },
    {
        "ID": 1022,
        "Name": "Greek"
    },
    {
        "ID": 1023,
        "Name": "Hindi"
    },
    {
        "ID": 1024,
        "Name": "Hungarian"
    },
    {
        "ID": 1025,
        "Name": "Indonesian"
    },
    {
        "ID": 1026,
        "Name": "Icelandic"
    },
    {
        "ID": 1027,
        "Name": "Hebrew"
    },
    {
        "ID": 1028,
        "Name": "Latvian"
    },
    {
        "ID": 1029,
        "Name": "Lithuanian"
    },
    {
        "ID": 1030,
        "Name": "Polish"
    },
    {
        "ID": 1031,
        "Name": "Russian"
    },
    {
        "ID": 1032,
        "Name": "Romanian"
    },
    {
        "ID": 1033,
        "Name": "Slovak"
    },
    {
        "ID": 1034,
        "Name": "Slovenian"
    },
    {
        "ID": 1035,
        "Name": "Serbian"
    },
    {
        "ID": 1036,
        "Name": "Ukrainian"
    },
    {
        "ID": 1037,
        "Name": "Turkish"
    },
    {
        "ID": 1038,
        "Name": "Catalan"
    },
    {
        "ID": 1039,
        "Name": "Croatian"
    },
    {
        "ID": 1040,
        "Name": "Vietnamese"
    },
    {
        "ID": 1041,
        "Name": "Urdu"
    },
    {
        "ID": 1042,
        "Name": "Filipino"
    },
    {
        "ID": 1043,
        "Name": "Estonian"
    },
    {
        "ID": 1044,
        "Name": "Thai"
    },
    {
        "ID": 1045,
        "Name": "Afar"
    },
    {
        "ID": 1046,
        "Name": "Abkhazian"
    },
    {
        "ID": 1047,
        "Name": "Afrikaans"
    },
    {
        "ID": 1048,
        "Name": "Amharic"
    },
    {
        "ID": 1049,
        "Name": "Assamese"
    },
    {
        "ID": 1050,
        "Name": "Aymara"
    },
    {
        "ID": 1051,
        "Name": "Azerbaijani"
    },
    {
        "ID": 1052,
        "Name": "Bashkir"
    },
    {
        "ID": 1053,
        "Name": "Belarusian"
    },
    {
        "ID": 1054,
        "Name": "Bihari"
    },
    {
        "ID": 1055,
        "Name": "Bislama"
    },
    {
        "ID": 1056,
        "Name": "Bengali"
    },
    {
        "ID": 1057,
        "Name": "Tibetan"
    },
    {
        "ID": 1058,
        "Name": "Breton"
    },
    {
        "ID": 1059,
        "Name": "Corsican"
    },
    {
        "ID": 1060,
        "Name": "Welsh"
    },
    {
        "ID": 1061,
        "Name": "Norwegian Nynorsk"
    },
    {
        "ID": 1062,
        "Name": "Esperanto"
    },
    {
        "ID": 1063,
        "Name": "Basque"
    },
    {
        "ID": 1064,
        "Name": "Persian"
    },
    {
        "ID": 1065,
        "Name": "Fijian"
    },
    {
        "ID": 1066,
        "Name": "Faroese"
    },
    {
        "ID": 1067,
        "Name": "Western Frisian"
    },
    {
        "ID": 1068,
        "Name": "Irish"
    },
    {
        "ID": 1069,
        "Name": "Scottish Gaelic"
    },
    {
        "ID": 1070,
        "Name": "Galician"
    },
    {
        "ID": 1071,
        "Name": "Guarani"
    },
    {
        "ID": 1072,
        "Name": "Gujarati"
    },
    {
        "ID": 1073,
        "Name": "Manx"
    },
    {
        "ID": 1074,
        "Name": "Hausa"
    },
    {
        "ID": 1075,
        "Name": "Bosnian"
    },
    {
        "ID": 1076,
        "Name": "Armenian"
    },
    {
        "ID": 1077,
        "Name": "Interlingua"
    },
    {
        "ID": 1078,
        "Name": "Interlingue"
    },
    {
        "ID": 1079,
        "Name": "Inupiaq"
    },
    {
        "ID": 1080,
        "Name": "Inuktitut"
    },
    {
        "ID": 1081,
        "Name": "Javanese"
    },
    {
        "ID": 1082,
        "Name": "Georgian"
    },
    {
        "ID": 1083,
        "Name": "Kazakh"
    },
    {
        "ID": 1084,
        "Name": "Greenlandic"
    },
    {
        "ID": 1085,
        "Name": "Khmer"
    },
    {
        "ID": 1086,
        "Name": "Kannada"
    },
    {
        "ID": 1087,
        "Name": "Kashmiri"
    },
    {
        "ID": 1088,
        "Name": "Kurdish"
    },
    {
        "ID": 1089,
        "Name": "Cornish"
    },
    {
        "ID": 1090,
        "Name": "Kirghiz"
    },
    {
        "ID": 1091,
        "Name": "Latin"
    },
    {
        "ID": 1092,
        "Name": "Luxembourgish"
    },
    {
        "ID": 1093,
        "Name": "Lingala"
    },
    {
        "ID": 1094,
        "Name": "Lao"
    },
    {
        "ID": 1095,
        "Name": "Malagasy"
    },
    {
        "ID": 1096,
        "Name": "Maori"
    },
    {
        "ID": 1097,
        "Name": "Macedonian"
    },
    {
        "ID": 1098,
        "Name": "Malayalam"
    },
    {
        "ID": 1099,
        "Name": "Mongolian"
    },
    {
        "ID": 1100,
        "Name": "Moldavian"
    },
    {
        "ID": 1101,
        "Name": "Marathi"
    },
    {
        "ID": 1102,
        "Name": "Malay"
    },
    {
        "ID": 1103,
        "Name": "Maltese"
    },
    {
        "ID": 1104,
        "Name": "Burmese"
    },
    {
        "ID": 1105,
        "Name": "Nauru"
    },
    {
        "ID": 1106,
        "Name": "Nepali"
    },
    {
        "ID": 1107,
        "Name": "Occitan"
    },
    {
        "ID": 1108,
        "Name": "(Afan) Oromo"
    },
    {
        "ID": 1109,
        "Name": "Oriya"
    },
    {
        "ID": 1110,
        "Name": "Punjabi"
    },
    {
        "ID": 1111,
        "Name": "Pushto"
    },
    {
        "ID": 1112,
        "Name": "Quechua"
    },
    {
        "ID": 1113,
        "Name": "Raeto-Romance"
    },
    {
        "ID": 1114,
        "Name": "Rundi"
    },
    {
        "ID": 1115,
        "Name": "Kinyarwanda"
    },
    {
        "ID": 1116,
        "Name": "Sanskrit"
    },
    {
        "ID": 1117,
        "Name": "Sindhi"
    },
    {
        "ID": 1118,
        "Name": "Northern S�mi"
    },
    {
        "ID": 1119,
        "Name": "Sango"
    },
    {
        "ID": 1120,
        "Name": "Zulu"
    },
    {
        "ID": 1121,
        "Name": "Sinhalese"
    },
    {
        "ID": 1122,
        "Name": "Samoan"
    },
    {
        "ID": 1123,
        "Name": "Shona"
    },
    {
        "ID": 1124,
        "Name": "Somali"
    },
    {
        "ID": 1125,
        "Name": "Albanian"
    },
    {
        "ID": 1126,
        "Name": "Swati"
    },
    {
        "ID": 1127,
        "Name": "Sotho"
    },
    {
        "ID": 1128,
        "Name": "Sundanese"
    },
    {
        "ID": 1129,
        "Name": "Swahili"
    },
    {
        "ID": 1130,
        "Name": "Tamil"
    },
    {
        "ID": 1131,
        "Name": "Telugu"
    },
    {
        "ID": 1132,
        "Name": "Tajik"
    },
    {
        "ID": 1133,
        "Name": "Tigrinya"
    },
    {
        "ID": 1134,
        "Name": "Turkmen"
    },
    {
        "ID": 1135,
        "Name": "Tswana"
    },
    {
        "ID": 1136,
        "Name": "Tonga"
    },
    {
        "ID": 1137,
        "Name": "Tsonga"
    },
    {
        "ID": 1138,
        "Name": "Tatar"
    },
    {
        "ID": 1139,
        "Name": "Twi"
    },
    {
        "ID": 1140,
        "Name": "Uighur"
    },
    {
        "ID": 1141,
        "Name": "Uzbek"
    },
    {
        "ID": 1142,
        "Name": "Volap�k"
    },
    {
        "ID": 1143,
        "Name": "Wolof"
    },
    {
        "ID": 1144,
        "Name": "Xhosa"
    },
    {
        "ID": 1145,
        "Name": "Yiddish"
    },
    {
        "ID": 1146,
        "Name": "Yoruba"
    },
    {
        "ID": 1147,
        "Name": "Zhuang"
    },
    {
        "ID": 1148,
        "Name": "English (Australia)"
    },
    {
        "ID": 1149,
        "Name": "Portuguese (Portugal)"
    },
    {
        "ID": 1150,
        "Name": "Chinese (Hong Kong SAR)"
    }
]

# SEO Tab
with tab1:
    st.subheader("SEO Keyword Generator & Suggestion")
    # User input field
    seo_keywords = st.text_input(
        "Enter SEO Keywords (comma-separated):", 
        key="seo_key",
        placeholder="e.g., SEO, Machine Learning, Automation"
    )

    # Process input when user submits
    if seo_keywords:
        keywords_list = [kw.strip() for kw in seo_keywords.split(",") if kw.strip()]     
        keywords_list = keywords_list[:10]

        st.success(f"✅ Using the first {len(keywords_list)} keywords: {', '.join(keywords_list)}")


    seo_description = st.text_area("Enter a Short Description (Optional):", key="seo_desc", 
                                placeholder="Describe your business or service for SEO")
    
    # Location and Language dropdowns
    st.subheader("Search Parameters")
    col1, col2 = st.columns(2)
    
    with col1:
        # Multi-select for locations
        selected_locations = st.multiselect(
            "Select Locations",
            options=[loc["country"] for loc in location_options],
            default=[location_options[0]["country"]],
            key="seo_locations"
        )
        
        # Get the location IDs based on selected location names
        location_ids = [
            loc["id"] for loc in location_options 
            if loc["country"] in selected_locations
        ]
    
    with col2:
        # Single select for language
        selected_language = st.selectbox(
            "Select Language",
            options=[lang["Name"] for lang in language_options],
            index=0,
            key="seo_language"
        )
        
        # Get the language ID based on selected language name
        language_id = next(
            (lang["ID"] for lang in language_options if lang["Name"] == selected_language),
            None
        )
    
    # Checkbox to enable/disable the exclusion filter
    use_exclude_filter = st.checkbox("Enable Exclusion Filter")
    if use_exclude_filter:
        max_exclude = st.slider(
            "Exclude Keywords with Monthly Searches Below",
            min_value=0,
            max_value=500,
            value=0,
            step=10,
            key="seo_exclude"
        )
    else:
        max_exclude = None


    # Generate exclusion list
    if max_exclude is None:
        exclude_values = []
    else:
        exclude_values = list(range(0, max_exclude + 1, 10))  # Include max_exclude in the range

        # Ensure the max_exclude is in the list if it's not already there
        if max_exclude > 0 and max_exclude not in exclude_values:
            exclude_values.append(int(max_exclude))



    st.caption(f"Will exclude keywords with monthly searches in: {exclude_values}")
    
    def fetch_seo_keywords(api_url):
        if not seo_keywords and not seo_description:
            st.error("Please provide at least one input (keywords or description).")
            return
        
        if not location_ids:
            st.error("Please select at least one location.")
            return
            
        if language_id is None:
            st.error("Please select a language.")
            return

        # Create payload with the new required parameters
        payload = {
            "keywords": seo_keywords, 
            "description": seo_description,
            "exclude_values": exclude_values,  
            "location_ids": location_ids,
            "language_id": language_id
        }
        
        with st.spinner("Generating keywords..."):
            response = requests.post(api_url, json=payload)

        if response.status_code == 200:
            data = response.json()
            st.success("SEO Keywords Generated Successfully!")

            # Display extracted keywords as JSON
            # st.subheader("Extracted SEO Keywords:")
            # st.json(data)

            # Convert JSON list to DataFrame
            try: 
                keywords_list = json.loads(data) if isinstance(data, str) else data
                if isinstance(keywords_list, list) and all(isinstance(item, dict) for item in keywords_list):
                    df = pd.DataFrame(keywords_list)
                    st.session_state.seo_df = df
                else:
                    st.error("Unexpected JSON format received!")
            except json.JSONDecodeError:
                st.error("Failed to parse JSON response!")
        else:
            error_msg = "Unknown error"
            try:
                error_detail = response.json().get('detail', error_msg)
                error_msg = error_detail
            except:
                pass
            st.error(f"Error: {error_msg}")

    

    # Function to process SEO keywords using the clustering API
    def process_seo_keywords():
        if st.session_state.seo_df is None or st.session_state.seo_df.empty:
            st.error("No SEO data available to process.")
            return

        # Convert DataFrame to CSV (in-memory)
        csv_buffer = BytesIO()
        st.session_state.seo_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        # Send CSV file to FastAPI
        files = {"file": ("seo_keywords.csv", csv_buffer, "text/csv")}
        response = requests.post(CLUSTER_API_URL, files=files)

        if response.status_code == 200:
            st.success("SEO Keywords Processed Successfully!")
            processed_data = response.json()

            # Convert JSON response to DataFrame
            try:
                processed_df = pd.DataFrame(processed_data)
                st.session_state.seo_processed_df = processed_df
                st.subheader("Processed SEO Keywords DataFrame:")
                st.dataframe(processed_df)
            except Exception as e:
                st.error(f"Error converting processed data to DataFrame: {e}")
        else:
            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")

    # Buttons for generating and suggesting SEO keywords
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Generate SEO Keywords", key="gen_seo"):
            fetch_seo_keywords(GENERATE_API_URL)
            
    

    # Ensure session state variable exists
    if "seo_df" not in st.session_state:
        st.session_state.seo_df = pd.DataFrame({"Keyword": [], "Search Volume": []})

    # Show SEO DataFrame if available
    if st.session_state.seo_df is not None and not st.session_state.seo_df.empty:


        st.subheader("Editable SEO Keywords DataFrame:")

        # Add a checkbox column for deletion
        df = st.session_state.seo_df.copy()
        df["Delete"] = False  # Default unchecked
        edited_df = st.data_editor(df, key="seo_data_editor", num_rows="dynamic", use_container_width=True)

        # min_search = st.slider(
        # "Exclude Keywords Below Monthly Searches",
        # min_value=0,
        # max_value=int(st.session_state.seo_df["Avg Monthly Searches"].max()) if not st.session_state.seo_df.empty else 500,
        # value=0,
        # step=10,
        # key="seo_exclude"
        # )

        # # Apply the filter
        # filtered_df = st.session_state.seo_df[st.session_state.seo_df["Avg Monthly Searches"] >= min_search].copy()
        # Create button columns
        col1, col2, col3,col4, col5 = st.columns([1, 1, 1,1 ,1])  # Adjust layout as needed

        with col1:
            if st.button("Delete Selected Rows", key="delete_seo_rows"):
                st.session_state.seo_df = edited_df[edited_df["Delete"] == False].drop(columns=["Delete"])
                st.success("Selected rows deleted!")

        with col2:
            if st.button("Save SEO Changes", key="save_seo"):
                st.session_state.seo_df = edited_df.drop(columns=["Delete"])
                st.success("SEO Changes Saved!")

        with col5:
            if st.button("Process SEO Keywords", key="process_seo"):
                process_seo_keywords()

        # Create another row of buttons
        # col4, col5 = st.columns([1, 1])

        with col4:
            if st.session_state.seo_df is not None and not st.session_state.seo_df.empty:
                csv = st.session_state.seo_df.to_csv(index=False)
                st.download_button(label="Download SEO CSV", data=csv, file_name="seo_keywords.csv", mime="text/csv", key="download_seo")

        with col3:
            if st.button("Clear SEO DataFrame", key="clear_seo"):
                st.session_state.seo_df = None
                st.session_state.seo_processed_df = None
                st.success("SEO Data Cleared!")
                
        # Show Processed SEO Keywords DataFrame if available
        if st.session_state.seo_processed_df is not None:
            st.subheader("Processed SEO Keywords DataFrame:")
            st.dataframe(st.session_state.seo_processed_df)

# PPC Tab
with tab2:
    st.header("PPC Keyword Generator")
    
    # User Input for PPC
    ppc_keywords = st.text_input("Enter PPC Keywords (comma-separated):", key="ppc_keywords", 
                                 placeholder="e.g., Google Ads, PPC Campaign, CPC")
    ppc_description = st.text_area("Enter a Short Description (Optional):", key="ppc_description", 
                                   placeholder="Describe your PPC campaign goals")

    



with tab3:
    st.header("Keywords Suggestion")
    
    # User Input for SEO
    seo_keywords = st.text_input("Enter SEO Keywords (comma-separated):", key="suggestion_key", 
                                 placeholder="e.g., SEO, Machine Learning, Automation")
    seo_description = st.text_area("Enter a Short Description (Optional):", key="suggestion_desc", 
                                   placeholder="Describe your business or service for SEO")        
    

    # Function to fetch additional suggested SEO keywords
    def fetch_suggested_seo_keywords():
        if not seo_keywords:
            st.error("Please provide some keywords for suggestions.")
            return

        payload = {"keywords": seo_keywords, "description": seo_description}
        response = requests.post(SUGGEST_API_URL, json=payload)
        
        if response.status_code == 200:
            suggested_keywords = response.json()
            st.success("Suggested SEO Keywords Generated!")

            st.write(suggested_keywords)
        else:
            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Suggest More SEO Keywords", key="suggest_seo"):
            fetch_suggested_seo_keywords()        