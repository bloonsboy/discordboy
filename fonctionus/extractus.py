import os
import zipfile

CSV_FILE_NAME = "package_messages.csv"

def check_csv_exists():
    """Verify if the CSV file exists."""
    return os.path.exists(CSV_FILE_NAME)

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