"""
Zenodo API client with rate limiting, retry logic, and comprehensive error handling.
Handles all interactions with the Zenodo REST API.
"""

import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urljoin, urlparse
from uuid import UUID

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.logger import get_logger


class ZenodoAPIError(Exception):
    """Bounded diagnostics; callers must supply fixed, credential-free messages."""

    def __init__(self, message, *, stage='api_request', exception_type='unknown',
                 status=None, retryable=False, attempt=1):
        stages = {'constructor_probe', 'api_request', 'bucket_upload', 'request_prepare',
                  'transport', 'response_status', 'response_json', 'response_owner', 'response_links',
                  'response_cleanup'}
        types = {'unknown', 'HTTPStatus', 'ProxyError', 'SSLError', 'ConnectTimeout',
                 'ReadTimeout', 'Timeout', 'ConnectionError', 'InvalidHeader',
                 'JSONDecodeError', 'RequestException', 'ValueError', 'AssertionError'}
        self.diagnostics = {
            'stage': stage if stage in stages else 'api_request',
            'exception_type': exception_type if exception_type in types else 'unknown',
            'status': status if type(status) is int and 100 <= status <= 599 else None,
            'retryable': retryable is True,
            'attempt': attempt if type(attempt) is int and 1 <= attempt <= 100 else 1,
        }
        # Call sites supply fixed messages; constructor wrapping discards originals.
        suffix = (' [' + ', '.join(f'{key}={value}' for key, value in self.diagnostics.items()) + ']'
                  if stage != 'api_request' or exception_type != 'unknown' or status is not None
                  or retryable or attempt != 1 else '')
        super().__init__(message + suffix)


def _exception_diagnostics(exc, stage, attempt=1):
    if isinstance(exc, ZenodoAPIError):
        return dict(exc.diagnostics)
    for cls, label, retryable in (
            (requests.exceptions.JSONDecodeError, 'JSONDecodeError', False),
            (requests.exceptions.ProxyError, 'ProxyError', False),
            (requests.exceptions.SSLError, 'SSLError', False),
            (requests.exceptions.InvalidHeader, 'InvalidHeader', False),
            (requests.exceptions.ConnectTimeout, 'ConnectTimeout', True),
            (requests.exceptions.ReadTimeout, 'ReadTimeout', True),
            (requests.exceptions.Timeout, 'Timeout', True),
            (requests.exceptions.ConnectionError, 'ConnectionError', True),
            (requests.exceptions.RequestException, 'RequestException', False),
            (ValueError, 'ValueError', False), (AssertionError, 'AssertionError', False)):
        if isinstance(exc, cls):
            return {'stage': stage, 'exception_type': label, 'status': None,
                    'retryable': retryable, 'attempt': attempt}
    return {'stage': stage, 'exception_type': 'unknown', 'status': None,
            'retryable': False, 'attempt': attempt}


class RateLimitError(ZenodoAPIError):
    """Exception raised when rate limit is exceeded."""
    pass


def _validate_token(token: str) -> str:
    """Accept opaque printable ASCII tokens without whitespace; never echo input."""
    if (not isinstance(token, str) or not token
            or any(ord(char) <= 32 or ord(char) >= 127 for char in token)):
        raise ValueError('Zenodo token must be nonempty printable ASCII without whitespace')
    return token


class ZenodoAPIClient:
    """Client for interacting with the Zenodo REST API."""
    
    def __init__(self, access_token: str, sandbox: bool = True):
        self.access_token = _validate_token(access_token)
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
            response = self._make_request('GET', 'deposit/depositions',
                                          _diagnostic_stage='constructor_probe', _retry=False,
                                          allow_redirects=False)
            if response.status_code == 200:
                self.logger.log_info("Zenodo API connection successful")
            else:
                raise ZenodoAPIError('API connection failed', stage='constructor_probe',
                                     exception_type='HTTPStatus', status=response.status_code)
        except Exception as exc:
            # Exception text and chained tracebacks can contain Authorization.
            raise ZenodoAPIError('Zenodo constructor probe failed',
                                 **_exception_diagnostics(exc, 'constructor_probe')) from None
    
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
    
    def _make_request(self, method: str, endpoint: str, *, _diagnostic_stage='api_request',
                      _retry=True, **kwargs) -> requests.Response:
        """Make a rate-limited request to the Zenodo API."""
        self._rate_limit_check()
        
        url = urljoin(self.api_url, endpoint)
        
        retries = self.max_retries if method.upper() in {"GET", "HEAD"} and _retry else 0
        kwargs.setdefault("timeout", 30)
        kwargs["allow_redirects"] = False
        for attempt in range(retries + 1):
            try:
                response = self.session.request(method, url, **kwargs)
                
                # Log request details
                self.api_logger.debug(
                    f"{method} {url} - Status: {response.status_code} - "
                    f"Attempt: {attempt + 1}/{self.max_retries + 1}"
                )
                
                if 300 <= response.status_code < 400:
                    raise ZenodoAPIError('API redirect refused', stage=_diagnostic_stage,
                                         exception_type='HTTPStatus', status=response.status_code)

                # Handle rate limiting
                if response.status_code == 429:
                    if attempt < retries:
                        retry_after = int(response.headers.get('Retry-After', 60))
                        self.logger.log_info(f"Rate limited, waiting {retry_after} seconds")
                        time.sleep(retry_after)
                        continue
                    else:
                        raise RateLimitError('Rate limit exceeded', stage=_diagnostic_stage,
                                             exception_type='HTTPStatus', status=429,
                                             retryable=True, attempt=attempt + 1)
                
                # Handle other errors
                if response.status_code >= 400:
                    if attempt < retries and response.status_code >= 500:
                        # Retry on server errors
                        delay = self.retry_delay * (self.backoff_factor ** attempt)
                        self.logger.log_info(f"Server error, retrying in {delay} seconds")
                        time.sleep(delay)
                        continue
                    else:
                        raise ZenodoAPIError('API request failed', stage=_diagnostic_stage,
                                             exception_type='HTTPStatus', status=response.status_code,
                                             retryable=response.status_code >= 500, attempt=attempt + 1)
                
                return response
                
            except requests.exceptions.RequestException as exc:
                diagnostics = _exception_diagnostics(exc, _diagnostic_stage, attempt + 1)
                if attempt < retries and diagnostics['retryable']:
                    delay = self.retry_delay * (self.backoff_factor ** attempt)
                    self.logger.log_info(f"Request failed, retrying in {delay} seconds")
                    time.sleep(delay)
                    continue
                else:
                    raise ZenodoAPIError('API transport failed', **diagnostics) from None
            except ZenodoAPIError as exc:
                error_class = RateLimitError if isinstance(exc, RateLimitError) else ZenodoAPIError
                raise error_class('API request failed',
                                  **_exception_diagnostics(exc, _diagnostic_stage, attempt + 1)) from None
            except Exception as exc:
                raise ZenodoAPIError('API request validation failed',
                                     **_exception_diagnostics(exc, _diagnostic_stage, attempt + 1)) from None
        
        raise ZenodoAPIError("Max retries exceeded")
    
    def _parse_error_response(self, response: requests.Response) -> str:
        """Keep diagnostics status-only: remote error bodies may echo credentials."""
        return f"HTTP {response.status_code}"
    
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
    
    def update_deposition_metadata(
        self,
        deposition_id: int,
        metadata: Dict[str, Any],
        files: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update deposition metadata, optionally toggling file settings."""
        data: Dict[str, Any] = {'metadata': metadata}
        if files is not None:
            data['files'] = files
        response = self._make_request('PUT', f'deposit/depositions/{deposition_id}', json=data)
        return response.json()
    
    def upload_file(self, deposition_id: int, file_path: str, filename: str = None) -> Dict[str, Any]:
        """Upload a file to a deposition using the new bucket API."""
        if filename is None:
            filename = os.path.basename(file_path)
        
        # Get deposition to get bucket URL
        deposition = self.get_deposition(deposition_id)
        if (not isinstance(deposition, dict) or type(deposition.get('id')) is not int
                or deposition['id'] != deposition_id):
            raise ZenodoAPIError('Bucket response does not identify the requested deposition')
        bucket_url = deposition['links']['bucket']
        bucket = urlparse(bucket_url)
        expected = 'sandbox.zenodo.org' if self.sandbox else 'zenodo.org'
        if (bucket.scheme != 'https' or bucket.hostname != expected
                or bucket.netloc != expected or bucket.query or bucket.fragment
                or not bucket.path.startswith('/api/files/')
                or len(bucket.path.strip('/').split('/')) != 3):
            raise ZenodoAPIError('File bucket URL does not match the selected environment')
        bucket_id = bucket.path.strip('/').split('/')[-1]
        try:
            if str(UUID(bucket_id)) != bucket_id:
                raise ValueError('Noncanonical bucket ID')
        except ValueError as exc:
            raise ZenodoAPIError('File bucket requires a canonical UUID identifier') from exc
        if (not isinstance(filename, str) or not filename or filename in ('.', '..')
                or '/' in filename or '\\' in filename):
            raise ZenodoAPIError('File upload requires a safe basename')
        
        # Upload file to bucket
        upload_url = f"{bucket_url.rstrip('/')}/{quote(filename, safe='')}"
        
        with open(file_path, 'rb') as f:
            # Use direct requests call to avoid Content-Type header issues
            headers = {'Authorization': f'Bearer {self.access_token}'}
            try:
                response = requests.put(upload_url, data=f, headers=headers,
                                        timeout=(10, 60), allow_redirects=False)
            except Exception as exc:
                raise ZenodoAPIError('File upload request failed',
                                     **_exception_diagnostics(exc, 'bucket_upload')) from None
            
            if response.status_code not in [200, 201]:
                raise ZenodoAPIError(f"File upload failed with HTTP {response.status_code}")
        
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
    
    def get_records_by_query(self, **params) -> List[Dict[str, Any]]:
        """Return only a structurally valid, complete exact-total inventory."""
        aggregated_hits = []
        params = dict(params)
        size = params.get('size', 100)
        page, expected_total = 1, None
        seen_ids = set()
        while True:
            response = self.search_records(**dict(params, page=page, size=size))
            container = response.get('hits') if isinstance(response, dict) else None
            if not isinstance(container, dict) or not isinstance(container.get('hits'), list):
                raise ValueError('Malformed record inventory response')
            total = container.get('total')
            if isinstance(total, dict):
                if total.get('relation', 'eq') != 'eq':
                    raise ValueError('Inventory total is not exact')
                total = total.get('value')
            if type(total) is not int or total < 0:
                raise ValueError('Inventory lacks exact total')
            if expected_total is not None and total != expected_total:
                raise ValueError('Inventory changed during pagination')
            expected_total = total
            hits = container['hits']
            if any(not isinstance(hit, dict) for hit in hits):
                raise ValueError('Malformed inventory record')
            for hit in hits:
                identifier = hit.get('id')
                if type(identifier) is not int or identifier < 1 or identifier in seen_ids:
                    raise ValueError('Invalid or repeated inventory record ID')
                seen_ids.add(identifier)
            aggregated_hits.extend(hits)
            if len(aggregated_hits) == total:
                return aggregated_hits
            if len(aggregated_hits) > total or not hits or not response.get('links', {}).get('next'):
                raise ValueError('Incomplete inventory pagination')
            page += 1

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
    
    def get_all_my_depositions(
        self,
        query: Optional[str] = None,
        modified_since: Optional[datetime] = None,
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get depositions for the authenticated user, optionally filtered by query or modification date."""
        all_depositions = []
        seen_ids = set()
        page = 1
        
        base_query = query or ""
        if modified_since:
            since_str = modified_since.strftime("%Y-%m-%dT%H:%M:%SZ")
            time_clause = f'modified:[{since_str} TO *]'
            base_query = f"{base_query} AND {time_clause}" if base_query else time_clause
        
        base_params = {}
        if base_query:
            base_params["q"] = base_query
        
        while True:
            params = {'page': page, 'size': page_size}
            params.update(base_params)
            response = self._make_request('GET', 'deposit/depositions', params=params)
            depositions = response.json()
            if not isinstance(depositions, list):
                raise ValueError('Malformed owned-draft inventory response')
            for deposition in depositions:
                identifier = deposition.get('id') if isinstance(deposition, dict) else None
                if type(identifier) is not int or identifier < 1 or identifier in seen_ids:
                    raise ValueError('Invalid or repeated owned-draft inventory ID')
                seen_ids.add(identifier)
            if not depositions:
                break
                
            all_depositions.extend(depositions)
            
            # If we got fewer than size results, we're on the last page
            if len(depositions) < page_size:
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
    """Prefer the selected environment token, then the legacy cwd .env file.

    Environment values are opaque (including NetworkSecret placeholders): never
    strip, expand, resolve, or log them. Invalid tokens fail closed; an empty
    environment variable uses the file fallback.
    """
    token_key = 'ZENODO_SANDBOX_TOKEN' if sandbox else 'ZENODO_PRODUCTION_TOKEN'
    environment_token = os.environ.get(token_key)
    if environment_token:
        return _validate_token(environment_token)

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
                    return _validate_token(value.strip())
                elif key.strip() == 'ZENODO_PRODUCTION_TOKEN' and not sandbox:
                    return _validate_token(value.strip())
    
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
