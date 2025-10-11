#!/usr/bin/env python3
"""
Test script for batch upload functionality with a small number of files.
"""

import os
import glob
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.batch_upload import BatchUploader

def main():
    """Test batch upload with a small number of files."""
    
    # Get a small sample of files for testing
    json_pattern = "output/zenodo_json/*.json"
    all_files = glob.glob(json_pattern)
    test_files = all_files[:5]  # Test with first 5 files
    
    print(f"Testing batch upload with {len(test_files)} files:")
    for f in test_files:
        print(f"  - {os.path.basename(f)}")
    
    # Create test uploader with small batch size
    uploader = BatchUploader(
        output_dir="output",
        sandbox=True,
        batch_size=5
    )
    
    try:
        # Upload the test batch
        result = uploader.upload_batch(test_files, 1)
        
        print(f"\nTest batch completed:")
        print(f"  Successful: {result['successful_uploads']}")
        print(f"  Failed: {result['failed_uploads']}")
        print(f"  Duration: {result['duration_seconds']:.1f} seconds")
        
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    main()
