import streamlit as st
import requests
from bs4 import BeautifulSoup
import os

# Load secrets
secrets = st.secrets["server"]

# Constants
DWD_URL = "https://data.dwd.de"
NGINX_URL = "http://nginx.eivissacopter.com:8080/wx/"  # Make sure to include the correct port

# Function to fetch the latest file URL from a given directory
def fetch_latest_file_url(directory_url):
    response = requests.get(directory_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    files = soup.find_all('a')
    latest_file_url = max(
        [directory_url + file['href'] for file in files if file['href'] not in ['../']],
        key=lambda file: requests.head(file).headers['Last-Modified']
    )
    return latest_file_url

# Function to download a file
def download_file(url, local_filename):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

# Function to upload file to Nginx server using HTTP PUT
def upload_file_to_nginx(file_path, file_name):
    with open(file_path, 'rb') as file:
        response = requests.put(NGINX_URL + file_name, data=file)
    return response

# Streamlit UI
st.title("DWD Data Fetcher and Uploader")

directories = st.text_area("Enter DWD directories (one per line)").split()
if st.button("Fetch and Upload Latest Files"):
    for directory in directories:
        directory_url = f"{DWD_URL}/{directory}"
        st.write(f"Processing directory: {directory_url}")
        
        try:
            latest_file_url = fetch_latest_file_url(directory_url)
            st.write(f"Latest file URL: {latest_file_url}")
            
            local_filename = latest_file_url.split('/')[-1]
            download_file(latest_file_url, local_filename)
            
            response = upload_file_to_nginx(local_filename, local_filename)
            if response.status_code in [200, 201, 204]:
                st.write(f"Successfully uploaded {local_filename} to Nginx server.")
            else:
                st.write(f"Failed to upload {local_filename}. Server responded with status code: {response.status_code}")
            
            os.remove(local_filename)
        except Exception as e:
            st.write(f"Error processing directory {directory}: {e}")

# Secrets.toml
# ```
# [server]
# server = "data.dwd.de"
# port = "2424"
# username = "wv22"
# password = "pGCabj;Iqv!wv7fbzjSVy"
# ```

# Function to test if Nginx server is configured correctly
def test_nginx_server():
    test_file_name = "test_file.txt"
    with open(test_file_name, 'w') as file:
        file.write("This is a test file.")
    
    response = upload_file_to_nginx(test_file_name, test_file_name)
    os.remove(test_file_name)
    return response.status_code in [200, 201, 204]

if st.button("Test Nginx Server Configuration"):
    if test_nginx_server():
        st.success("Nginx server is configured correctly.")
    else:
        st.error("Failed to store files on Nginx server.")
