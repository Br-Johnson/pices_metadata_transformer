#!/usr/bin/env python3
"""
Resume upload script that skips already uploaded files and continues from where it left off.
"""

import os
import json
import glob
from upload_to_zenodo import ZenodoUploader

def get_uploaded_files(log_file_path):
    """Extract list of already uploaded files from the log."""
    uploaded_files = set()
    
    if os.path.exists(log_file_path):
        with open(log_file_path, 'r') as f:
            for line in f:
                if "Successfully uploaded" in line:
                    # Extract filename from log line like:
                    # "2025-10-11 07:17:12,436 - INFO - Successfully uploaded FGDC-2310 - Deposition ID: 351527, DOI: 10.5281/zenodo.351527"
                    parts = line.split("Successfully uploaded ")
                    if len(parts) > 1:
                        filename = parts[1].split(" - ")[0]
                        uploaded_files.add(filename)
    
    return uploaded_files

def main():
    """Resume upload from where it left off."""
    print("=== Resuming Zenodo Upload ===")
    
    # Get list of already uploaded files
    log_file = "logs/transform_run_20251011_030709.log"
    uploaded_files = get_uploaded_files(log_file)
    
    print(f"Found {len(uploaded_files)} already uploaded files")
    print(f"Last uploaded: {max(uploaded_files) if uploaded_files else 'None'}")
    
    # Get all JSON files
    json_pattern = "output/zenodo_json/*.json"
    all_json_files = glob.glob(json_pattern)
    all_json_files.sort()
    
    print(f"Total JSON files: {len(all_json_files)}")
    
    # Filter out already uploaded files
    remaining_files = []
    for json_file in all_json_files:
        filename = os.path.basename(json_file).replace('.json', '')
        if filename not in uploaded_files:
            remaining_files.append(json_file)
    
    print(f"Remaining files to upload: {len(remaining_files)}")
    
    if not remaining_files:
        print("All files have been uploaded!")
        return
    
    # Create uploader and continue upload
    uploader = ZenodoUploader(output_dir="output", sandbox=True)
    
    print(f"Resuming upload with {len(remaining_files)} remaining files...")
    uploader.upload_files(remaining_files)

if __name__ == "__main__":
    main()
