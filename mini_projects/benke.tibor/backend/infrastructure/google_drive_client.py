"""
Google Drive API client for accessing shared folders.
Handles OAuth 2.0 authentication and file operations.
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle

logger = logging.getLogger(__name__)

# Scopes required for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


class GoogleDriveClient:
    """
    Google Drive API client for reading files from shared folders.
    Uses OAuth 2.0 for authentication.
    """
    
    def __init__(self, credentials_dir: Optional[str] = None):
        """
        Initialize Google Drive client.
        
        Args:
            credentials_dir: Directory containing client_secret.json and token.json
        """
        if credentials_dir is None:
            # Default to backend/credentials/
            backend_path = Path(__file__).parent.parent
            credentials_dir = backend_path / "credentials"
        
        self.credentials_dir = Path(credentials_dir)
        self.client_secret_path = self.credentials_dir / "client_secret.json"
        self.token_path = self.credentials_dir / "token.json"
        self.service = None
        
        logger.info(f"GoogleDriveClient initialized with credentials_dir: {self.credentials_dir}")
    
    def authenticate(self) -> None:
        """
        Authenticate with Google Drive API using OAuth 2.0.
        Creates token.json after first successful authentication.
        """
        creds = None
        
        # Check if token.json exists (already authenticated)
        if self.token_path.exists():
            logger.info("Loading existing credentials from token.json")
            try:
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                logger.warning(f"Failed to load token.json: {e}")
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired credentials")
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Failed to refresh token: {e}")
                    # If refresh fails, need to re-authenticate
                    creds = None
            
            if not creds:
                if not self.client_secret_path.exists():
                    raise FileNotFoundError(
                        f"client_secret.json not found at {self.client_secret_path}. "
                        f"Download it from Google Cloud Console and place it in backend/credentials/"
                    )
                
                logger.info("Starting OAuth 2.0 flow")
                logger.warning(
                    "⚠️  OAuth authentication required! "
                    "If running in Docker, you must authenticate locally first. "
                    "See docs/GOOGLE_DRIVE_SETUP.md for instructions."
                )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.client_secret_path), SCOPES
                )
                
                # Try to run local server
                try:
                    creds = flow.run_local_server(port=0)
                    logger.info("✅ Authentication successful!")
                except Exception as e:
                    logger.error(
                        f"❌ OAuth flow failed: {e}\n"
                        f"Please authenticate locally first:\n"
                        f"1. Run outside Docker: python backend/scripts/authenticate_google_drive.py\n"
                        f"2. Or copy token.json from local machine to backend/credentials/"
                    )
                    raise RuntimeError(
                        "OAuth authentication failed. Cannot run OAuth flow in Docker without browser. "
                        "Please authenticate locally first and copy token.json to backend/credentials/"
                    )
            
            # Save credentials for future use
            logger.info("Saving credentials to token.json")
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        # Build service
        self.service = build('drive', 'v3', credentials=creds)
        logger.info("Google Drive service authenticated successfully")
    
    def list_files_in_folder(
        self, 
        folder_id: str, 
        page_size: int = 100,
        mime_type_filter: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        List all files in a Google Drive folder.
        
        Args:
            folder_id: Google Drive folder ID (from URL)
            page_size: Maximum number of files to return per page
            mime_type_filter: Optional MIME type filter (e.g., 'application/pdf')
        
        Returns:
            List of dictionaries with file metadata (id, name, mimeType, size, etc.)
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            # Build query
            query = f"'{folder_id}' in parents and trashed=false"
            if mime_type_filter:
                query += f" and mimeType='{mime_type_filter}'"
            
            files = []
            page_token = None
            
            while True:
                # List files
                response = self.service.files().list(
                    q=query,
                    pageSize=page_size,
                    fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, webViewLink)",
                    pageToken=page_token
                ).execute()
                
                batch = response.get('files', [])
                files.extend(batch)
                
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
            
            logger.info(f"Found {len(files)} files in folder {folder_id}")
            return files
        
        except HttpError as error:
            logger.error(f"Google Drive API error: {error}")
            raise
    
    def get_file_metadata(self, file_id: str) -> Dict[str, str]:
        """
        Get metadata for a specific file.
        
        Args:
            file_id: Google Drive file ID
        
        Returns:
            Dictionary with file metadata
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, createdTime, modifiedTime, webViewLink"
            ).execute()
            
            logger.info(f"Retrieved metadata for file: {file.get('name')}")
            return file
        
        except HttpError as error:
            logger.error(f"Google Drive API error: {error}")
            raise
    
    def download_file_content(self, file_id: str) -> bytes:
        """
        Download file content from Google Drive.
        
        Args:
            file_id: Google Drive file ID
        
        Returns:
            File content as bytes
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            # For Google Workspace files, export as PDF
            file_metadata = self.get_file_metadata(file_id)
            mime_type = file_metadata.get('mimeType', '')
            
            if mime_type.startswith('application/vnd.google-apps'):
                # Google Workspace file - export as PDF
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='application/pdf'
                )
            else:
                # Regular file - download directly
                request = self.service.files().get_media(fileId=file_id)
            
            content = request.execute()
            logger.info(f"Downloaded file: {file_metadata.get('name')} ({len(content)} bytes)")
            return content
        
        except HttpError as error:
            logger.error(f"Google Drive API error: {error}")
            raise


# Singleton instance
_drive_client = None


def get_drive_client() -> GoogleDriveClient:
    """Get or create singleton Google Drive client instance."""
    global _drive_client
    if _drive_client is None:
        _drive_client = GoogleDriveClient()
    return _drive_client
