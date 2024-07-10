import streamlit as st

def set_page_config():
    st.set_page_config(page_title="HEMSreach", page_icon=":helicopter:", layout="wide")

def apply_custom_css():
    st.markdown(
        """
        <style>
        body {
            background-color: #2e2e2e;
            color: white;
        }
        .reportview-container .main .block-container {
            padding: 0;
        }
        .reportview-container .main {
            background: none;
            padding: 0;
        }
        .sidebar .sidebar-content {
            background-color: #3e3e3e;
        }
        .fullScreenMap {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0;
        }
        .stSlider, .stNumberInput, .stTextInput {
            color: black;
        }
        .stNumberInput, .stTextInput {
            display: inline-block;
            margin-right: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
