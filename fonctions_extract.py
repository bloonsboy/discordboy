import json
import os
import pandas as pd
from tqdm import tqdm
from datetime import datetime, timedelta
from collections import defaultdict
import zipfile
import matplotlib.pyplot as plt
import re

MESSAGE_TYPES = ["DM", "GROUP_DM", "GUILD_TEXT", "PUBLIC_THREAD"]

####################
### EXTRACT DATA ###
####################

def ask_package():   
    '''
    Ask the user for the path of the package.zip file
    ''' 
    choice = input("Enter the name of the package").strip()
    if not choice.endswith('.zip'):
        choice += '.zip'
    print("Package name : ", choice)
    return choice

def extract_zip(zip_path):
    '''
    Extract the package.zip file in the package folder
    '''
    zip_path = check_zip_path(zip_path)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(zip_path[:-4])

def check_zip_path(zip_path):
    '''
    Check if the zip file exists at the given path or in the Downloads folder
    '''
    if not os.path.exists(zip_path):
        if zip_path.endswith('.zip'):
            zip_path = os.path.basename(zip_path)
        download_path = os.path.join(os.path.expanduser("~"), "Downloads", zip_path)
        documents_path = os.path.join(os.path.expanduser("~"), "Documents", zip_path)
        if os.path.exists(download_path) or os.path.exists(download_path[:-4]):
            zip_path = download_path
        elif os.path.exists(documents_path) or os.path.exists(documents_path[:-4]):
            zip_path = documents_path
        else:
            raise FileNotFoundError(f"Zip file not found at {zip_path} or {download_path} or {documents_path}")
    return zip_path

def get_conversion_name_dict(index_path):
    '''
    Get the dict conversion for ID - Name
    '''
    index_path = check_zip_path(index_path)
    with open(index_path, 'r', encoding='utf-8') as f:
        index_data = json.load(f)
    conversation_names = {key: value.replace("Direct Message with ", "").replace("#0", "") for key, value in index_data.items()}
    return conversation_names

def create_dataframe(messages_path, conversation_names):
    '''
    Create a DataFrame from the messages.json files
    '''
    rows = []
    messages_path = check_zip_path(messages_path)
    for folder_name in tqdm(os.listdir(messages_path), desc="Processing folder", unit="folder"):
        if folder_name.startswith('c'):
            name = conversation_names.get(folder_name[1:], "Unknown channel")
            type = get_channel_type(messages_path, folder_name)
            messages_data = load_messages(messages_path, folder_name)
            rows.extend(process_messages(messages_data, name, type))
    return pd.DataFrame.from_records(rows)

def get_channel_type(messages_path, folder_name):
    '''
    Get the type of the channel from channel.json
    '''
    channel_path = os.path.join(messages_path, folder_name, "channel.json")
    with open(channel_path, 'r', encoding='utf-8') as f:
        return json.load(f).get("type", "Unknown")

def load_messages(messages_path, folder_name):
    '''
    Load messages from messages.json
    '''
    messages_path = os.path.join(messages_path, folder_name, "messages.json")
    with open(messages_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def process_messages(messages_data, name, type):
    '''
    Process messages and return a list of rows
    '''
    rows = []
    for message in messages_data:
        id = message.get("ID", "No ID")
        content = message.get("Contents", "No content")
        date = datetime.strptime(message.get("Timestamp"), "%Y-%m-%d %H:%M:%S")
        attachments = message.get("Attachments", [])
        rows.append({
            "ID": id, 
            "Name": name, 
            "Type": type, 
            "Timestamp": date, 
            "Contents": content, 
            "Attachments": attachments
        })
    return rows
