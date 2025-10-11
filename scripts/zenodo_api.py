"""
Zenodo API client with rate limiting, retry logic, and comprehensive error handling.
Handles all interactions with the Zenodo REST API.
"""

import requests
import json
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urljoin
import logging
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.logger import get_logger


class ZenodoAPIError(Exception):
    """Custom exception for Zenodo API errors."""
    pass


class RateLimitError(ZenodoAPIError):
    """Exception raised when rate limit is exceeded."""
    pass


class ZenodoAPIClient:
    """Client for interacting with the Zenodo REST API."""
    
    def __init__(self, access_token: str, sandbox: bool = True):
        self.access_token = access_token
        self.sandbox = sandbox
        self.base_url = "https://sandbox.zenodo.org" if sandbox else "https://zenodo.org"
        self.api_url = urljoin(self.base_url, "/api/")
        
        # Rate limiting - stay within Zenodo limits (5000/hour, 100/minute)
        self.requests_per_minute = 90  # Stay safely under 100/minute limit
        self.requests_per_hour = 4500  # Stay safely under 5000/hour limit
        self.request_times = []
        self.hourly_request_times = []
        self.min_request_interval = 0.7  # ~85 requests/minute with safety margin
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        self.backoff_factor = 2
        
        # Setup session with proper cleanup
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        })
        
        # Add connection pooling and timeout settings
        self.session.mount('https://', requests.adapters.HTTPAdapter(
            pool_connections=1,
            pool_maxsize=1,
            max_retries=0  # We handle retries ourselves
        ))
        
        # Setup logging
        self.logger = get_logger()
        self.api_logger = logging.getLogger('zenodo_api')
        self.api_logger.setLevel(logging.DEBUG)
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test API connection and token validity."""
        try:
            response = self._make_request('GET', 'deposit/depositions')
            if response.status_code == 200:
                self.logger.log_info("Zenodo API connection successful")
            else:
                raise ZenodoAPIError(f"API connection failed: {response.status_code}")
        except Exception as e:
            raise ZenodoAPIError(f"Failed to connect to Zenodo API: {str(e)}")
    
    def _rate_limit_check(self):
        """Check and enforce rate limiting for both minute and hour limits."""
        now = datetime.now()
        
        # Check minimum interval between requests
        if self.request_times:
            last_request = self.request_times[-1]
            time_since_last = (now - last_request).total_seconds()
            if time_since_last < self.min_request_interval:
                wait_time = self.min_request_interval - time_since_last
                self.logger.log_info(f"Rate limit reached, waiting {wait_time:.1f} seconds")
                time.sleep(wait_time)
                now = datetime.now()  # Update now after sleep
        
        # Clean up old request times
        self.request_times = [
            req_time for req_time in self.request_times
            if now - req_time < timedelta(minutes=1)
        ]
        
        self.hourly_request_times = [
            req_time for req_time in self.hourly_request_times
            if now - req_time < timedelta(hours=1)
        ]
        
        # Check minute limit
        if len(self.request_times) >= self.requests_per_minute:
            oldest_request = min(self.request_times)
            wait_until = oldest_request + timedelta(minutes=1)
            wait_seconds = (wait_until - now).total_seconds()
            
            if wait_seconds > 0:
                self.logger.log_info(f"Minute rate limit reached, waiting {wait_seconds:.1f} seconds")
                time.sleep(wait_seconds)
                now = datetime.now()
        
        # Check hour limit
        if len(self.hourly_request_times) >= self.requests_per_hour:
            oldest_request = min(self.hourly_request_times)
            wait_until = oldest_request + timedelta(hours=1)
            wait_seconds = (wait_until - now).total_seconds()
            
            if wait_seconds > 0:
                self.logger.log_info(f"Hourly rate limit reached, waiting {wait_seconds:.1f} seconds")
                time.sleep(wait_seconds)
                now = datetime.now()
        
        # Record this request
        self.request_times.append(now)
        self.hourly_request_times.append(now)
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make a rate-limited request to the Zenodo API."""
        self._rate_limit_check()
        
        url = urljoin(self.api_url, endpoint)
        
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, url, **kwargs)
                
                # Log request details
                self.api_logger.debug(
                    f"{method} {url} - Status: {response.status_code} - "
                    f"Attempt: {attempt + 1}/{self.max_retries + 1}"
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    if attempt < self.max_retries:
                        retry_after = int(response.headers.get('Retry-After', 60))
                        self.logger.log_info(f"Rate limited, waiting {retry_after} seconds")
                        time.sleep(retry_after)
                        continue
                    else:
                        raise RateLimitError("Rate limit exceeded after retries")
                
                # Handle other errors
                if response.status_code >= 400:
                    error_msg = self._parse_error_response(response)
                    if attempt < self.max_retries and response.status_code >= 500:
                        # Retry on server errors
                        delay = self.retry_delay * (self.backoff_factor ** attempt)
                        self.logger.log_info(f"Server error, retrying in {delay} seconds")
                        time.sleep(delay)
                        continue
                    else:
                        raise ZenodoAPIError(f"API error: {error_msg}")
                
                return response
                
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries:
                    delay = self.retry_delay * (self.backoff_factor ** attempt)
                    self.logger.log_info(f"Request failed, retrying in {delay} seconds: {str(e)}")
                    time.sleep(delay)
                    continue
                else:
                    raise ZenodoAPIError(f"Request failed after retries: {str(e)}")
        
        raise ZenodoAPIError("Max retries exceeded")
    
    def _parse_error_response(self, response: requests.Response) -> str:
        """Parse error response from Zenodo API."""
        try:
            error_data = response.json()
            if 'message' in error_data:
                message = error_data['message']
                if 'errors' in error_data:
                    errors = error_data['errors']
                    error_details = []
                    for error in errors:
                        if 'field' in error and 'message' in error:
                            error_details.append(f"{error['field']}: {error['message']}")
                        else:
                            error_details.append(str(error))
                    return f"{message} - {'; '.join(error_details)}"
                return message
        except (json.JSONDecodeError, KeyError):
            pass
        
        return f"HTTP {response.status_code}: {response.text}"
    
    def create_deposition(self, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new deposition."""
        data = {}
        if metadata:
            data['metadata'] = metadata
        
        response = self._make_request('POST', 'deposit/depositions', json=data)
        return response.json()
    
    def get_deposition(self, deposition_id: int) -> Dict[str, Any]:
        """Get a deposition by ID."""
        response = self._make_request('GET', f'deposit/depositions/{deposition_id}')
        return response.json()
    
    def update_deposition_metadata(self, deposition_id: int, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Update deposition metadata."""
        data = {'metadata': metadata}
        response = self._make_request('PUT', f'deposit/depositions/{deposition_id}', json=data)
        return response.json()
    
    def upload_file(self, deposition_id: int, file_path: str, filename: str = None) -> Dict[str, Any]:
        """Upload a file to a deposition using the new bucket API."""
        if filename is None:
            filename = os.path.basename(file_path)
        
        # Get deposition to get bucket URL
        deposition = self.get_deposition(deposition_id)
        bucket_url = deposition['links']['bucket']
        
        # Upload file to bucket
        upload_url = f"{bucket_url}/{filename}"
        
        with open(file_path, 'rb') as f:
            # Use direct requests call to avoid Content-Type header issues
            headers = {'Authorization': f'Bearer {self.access_token}'}
            response = requests.put(upload_url, data=f, headers=headers)
            
            if response.status_code not in [200, 201]:
                raise ZenodoAPIError(f"File upload failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    def close(self):
        """Properly close the session and clean up resources."""
        if hasattr(self, 'session'):
            self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with proper cleanup."""
        self.close()
    
    def upload_file_legacy(self, deposition_id: int, file_path: str, filename: str = None) -> Dict[str, Any]:
        """Upload a file using the legacy API (for smaller files)."""
        if filename is None:
            filename = os.path.basename(file_path)
        
        data = {'name': filename}
        files = {'file': open(file_path, 'rb')}
        
        try:
            # Remove Content-Type header for multipart upload
            headers = {'Authorization': f'Bearer {self.access_token}'}
            response = self._make_request(
                'POST', 
                f'deposit/depositions/{deposition_id}/files',
                data=data,
                files=files,
                headers=headers
            )
            return response.json()
        finally:
            files['file'].close()
    
    def publish_deposition(self, deposition_id: int) -> Dict[str, Any]:
        """Publish a deposition."""
        response = self._make_request('POST', f'deposit/depositions/{deposition_id}/actions/publish')
        return response.json()
    
    def edit_deposition(self, deposition_id: int) -> Dict[str, Any]:
        """Unlock a deposition for editing."""
        response = self._make_request('POST', f'deposit/depositions/{deposition_id}/actions/edit')
        return response.json()
    
    def discard_deposition(self, deposition_id: int) -> Dict[str, Any]:
        """Discard changes to a deposition."""
        response = self._make_request('POST', f'deposit/depositions/{deposition_id}/actions/discard')
        return response.json()
    
    def delete_deposition(self, deposition_id: int) -> bool:
        """Delete a deposition (only unpublished ones)."""
        response = self._make_request('DELETE', f'deposit/depositions/{deposition_id}')
        return response.status_code == 204
    
    def list_depositions(self, **params) -> List[Dict[str, Any]]:
        """List depositions for the authenticated user."""
        response = self._make_request('GET', 'deposit/depositions', params=params)
        return response.json()
    
    def get_licenses(self) -> List[Dict[str, Any]]:
        """Get available licenses."""
        response = self._make_request('GET', 'licenses/')
        return response.json()
    
    def search_records(self, **params) -> Dict[str, Any]:
        """Search published records."""
        response = self._make_request('GET', 'records/', params=params)
        return response.json()
    
    def get_record(self, record_id: int) -> Dict[str, Any]:
        """Get a published record by ID."""
        response = self._make_request('GET', f'records/{record_id}')
        return response.json()
    
    def search_by_title(self, title: str) -> List[Dict[str, Any]]:
        """Search for depositions by title."""
        params = {
            'q': f'title:"{title}"',
            'size': 100  # Maximum results per page
        }
        response = self._make_request('GET', 'deposit/depositions', params=params)
        return response.json()
    
    def get_all_my_depositions(self) -> List[Dict[str, Any]]:
        """Get all depositions for the authenticated user."""
        all_depositions = []
        page = 1
        size = 100
        
        while True:
            params = {'page': page, 'size': size}
            response = self._make_request('GET', 'deposit/depositions', params=params)
            depositions = response.json()
            
            if not depositions:
                break
                
            all_depositions.extend(depositions)
            
            # If we got fewer than size results, we're on the last page
            if len(depositions) < size:
                break
                
            page += 1
        
        return all_depositions
    
    def search_depositions(self, query: str, **params) -> List[Dict[str, Any]]:
        """Search depositions with custom query and parameters."""
        search_params = {'q': query}
        search_params.update(params)
        
        response = self._make_request('GET', 'deposit/depositions', params=search_params)
        return response.json()


def load_zenodo_token(sandbox: bool = True) -> str:
    """Load Zenodo token from .env file."""
    secrets_file = ".env"
    
    if not os.path.exists(secrets_file):
        raise FileNotFoundError(f"Secrets file not found: {secrets_file}")
    
    with open(secrets_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                if key.strip() == 'ZENODO_SANDBOX_TOKEN' and sandbox:
                    return value.strip()
                elif key.strip() == 'ZENODO_PRODUCTION_TOKEN' and not sandbox:
                    return value.strip()
    
    raise ValueError(f"Token not found in {secrets_file}")


def create_zenodo_client(sandbox: bool = True, access_token: str = None) -> ZenodoAPIClient:
    """Create a Zenodo API client."""
    if access_token is None:
        access_token = load_zenodo_token(sandbox)
    
    return ZenodoAPIClient(access_token, sandbox)


# Example usage and testing functions
def test_api_connection(sandbox: bool = True):
    """Test API connection and basic functionality."""
    try:
        client = create_zenodo_client(sandbox)
        
        # Test listing depositions
        depositions = client.list_depositions()
        print(f"Found {len(depositions)} existing depositions")
        
        # Test getting licenses
        licenses = client.get_licenses()
        print(f"Found {len(licenses)} available licenses")
        
        print("API connection test successful!")
        return True
        
    except Exception as e:
        print(f"API connection test failed: {e}")
        return False


def create_test_deposition(sandbox: bool = True) -> Dict[str, Any]:
    """Create a test deposition for testing purposes."""
    client = create_zenodo_client(sandbox)
    
    test_metadata = {
        'title': 'Test Deposition - FGDC to Zenodo Migration',
        'upload_type': 'dataset',
        'publication_date': '2025-01-01',
        'creators': [{'name': 'Test, User'}],
        'description': 'This is a test deposition created during FGDC to Zenodo migration testing.',
        'access_right': 'open',
        'license': 'cc-zero',
        'keywords': ['test', 'migration', 'fgdc', 'zenodo'],
        'communities': [{'identifier': 'pices'}]
    }
    
    try:
        deposition = client.create_deposition(test_metadata)
        print(f"Created test deposition: {deposition['id']}")
        print(f"DOI: {deposition.get('metadata', {}).get('prereserve_doi', {}).get('doi', 'Not reserved')}")
        return deposition
    except Exception as e:
        print(f"Failed to create test deposition: {e}")
        raise


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test API connection
        sandbox = len(sys.argv) > 2 and sys.argv[2] == "sandbox"
        test_api_connection(sandbox)
    elif len(sys.argv) > 1 and sys.argv[1] == "create-test":
        # Create test deposition
        sandbox = len(sys.argv) > 2 and sys.argv[2] == "sandbox"
        create_test_deposition(sandbox)
    else:
        print("Usage:")
        print("  python zenodo_api.py test [sandbox]     - Test API connection")
        print("  python zenodo_api.py create-test [sandbox] - Create test deposition")
