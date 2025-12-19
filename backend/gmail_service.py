"""
Gmail Service - Send emails using Gmail API
"""
import os
import base64
import logging
from typing import Dict, Any, Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]


class GmailService:
    """Gmail API service for sending emails"""

    def __init__(self, credentials_file: Optional[str] = None, token_file: Optional[str] = None):
        """
        Initialize Gmail service

        Args:
            credentials_file: Path to OAuth credentials JSON file (from Google Cloud Console)
            token_file: Path to store/load OAuth token (auto-generated after first auth)
        """
        self.credentials_file = credentials_file or os.getenv('GMAIL_CREDENTIALS_FILE', 'credentials.json')
        self.token_file = token_file or os.getenv('GMAIL_TOKEN_FILE', 'token.json')
        self.service = None
        self.creds = None

    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API using OAuth 2.0

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Check if we have valid credentials
            if os.path.exists(self.token_file):
                logger.info(f"Loading credentials from {self.token_file}")
                self.creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

            # If credentials are not valid, refresh or create new ones
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    logger.info("Refreshing expired credentials")
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_file):
                        logger.error(f"Credentials file not found: {self.credentials_file}")
                        logger.error("Please download OAuth credentials from Google Cloud Console")
                        return False

                    logger.info("Starting OAuth flow...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)

                # Save credentials for next run
                with open(self.token_file, 'w') as token:
                    token.write(self.creds.to_json())
                logger.info(f"Credentials saved to {self.token_file}")

            # Build Gmail service
            self.service = build('gmail', 'v1', credentials=self.creds)
            logger.info("Gmail service authenticated successfully")
            return True

        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
            return False

    def create_message(
        self,
        to: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        html: bool = False
    ) -> Dict[str, Any]:
        """
        Create email message

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body text
            from_email: Sender email (optional, uses authenticated user if not provided)
            html: If True, body is HTML; otherwise plain text

        Returns:
            Gmail API message dict
        """
        try:
            message = MIMEMultipart() if html else MIMEText(body)

            if from_email:
                message['From'] = from_email
            message['To'] = to
            message['Subject'] = subject

            if html:
                msg_html = MIMEText(body, 'html')
                message.attach(msg_html)

            # Encode the message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            return {'raw': raw_message}

        except Exception as e:
            logger.error(f"Error creating message: {e}")
            raise

    def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        html: bool = False
    ) -> Dict[str, Any]:
        """
        Send email via Gmail API

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
            from_email: Sender email (optional)
            html: If True, body is HTML

        Returns:
            Gmail API response with message ID

        Raises:
            Exception if sending fails
        """
        # Ensure we're authenticated
        if not self.service:
            if not self.authenticate():
                raise Exception("Gmail authentication failed")

        try:
            # Create message
            message = self.create_message(to, subject, body, from_email, html)

            # Send message
            logger.info(f"Sending email to {to}: {subject}")
            result = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()

            logger.info(f"Email sent successfully. Message ID: {result.get('id')}")
            return result

        except HttpError as error:
            logger.error(f"Gmail API error: {error}")
            raise Exception(f"Failed to send email: {error}")
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            raise

    def list_messages(
        self,
        query: str = '',
        max_results: int = 10,
        label_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        List messages in Gmail inbox

        Args:
            query: Gmail search query (e.g., "from:user@example.com subject:order")
            max_results: Maximum number of messages to return
            label_ids: Filter by labels (e.g., ['INBOX', 'UNREAD'])

        Returns:
            List of message metadata dicts
        """
        if not self.service:
            if not self.authenticate():
                raise Exception("Gmail authentication failed")

        try:
            logger.info(f"Listing messages with query: '{query}', max: {max_results}")

            request_params = {
                'userId': 'me',
                'maxResults': max_results
            }

            if query:
                request_params['q'] = query

            if label_ids:
                request_params['labelIds'] = label_ids

            result = self.service.users().messages().list(**request_params).execute()

            messages = result.get('messages', [])
            logger.info(f"Found {len(messages)} messages")

            return messages

        except HttpError as error:
            logger.error(f"Gmail API error listing messages: {error}")
            raise Exception(f"Failed to list messages: {error}")

    def get_message(self, message_id: str, format: str = 'full') -> Dict[str, Any]:
        """
        Get full message details

        Args:
            message_id: Gmail message ID
            format: 'full', 'metadata', 'minimal', or 'raw'

        Returns:
            Message dict with headers, body, etc.
        """
        if not self.service:
            if not self.authenticate():
                raise Exception("Gmail authentication failed")

        try:
            logger.info(f"Getting message: {message_id}")

            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format=format
            ).execute()

            return message

        except HttpError as error:
            logger.error(f"Gmail API error getting message: {error}")
            raise Exception(f"Failed to get message: {error}")

    def parse_message_body(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse message to extract useful fields

        Args:
            message: Message dict from get_message()

        Returns:
            Dict with from, to, subject, body, date, etc.
        """
        headers = message.get('payload', {}).get('headers', [])

        # Extract headers
        parsed = {
            'id': message.get('id'),
            'threadId': message.get('threadId'),
            'snippet': message.get('snippet', ''),
            'from': '',
            'to': '',
            'subject': '',
            'date': '',
            'body': ''
        }

        for header in headers:
            name = header.get('name', '').lower()
            value = header.get('value', '')

            if name == 'from':
                parsed['from'] = value
            elif name == 'to':
                parsed['to'] = value
            elif name == 'subject':
                parsed['subject'] = value
            elif name == 'date':
                parsed['date'] = value

        # Extract body
        payload = message.get('payload', {})

        # Try to get plain text body
        if 'parts' in payload:
            for part in payload['parts']:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/plain':
                    body_data = part.get('body', {}).get('data', '')
                    if body_data:
                        parsed['body'] = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        break
        else:
            # Single part message
            body_data = payload.get('body', {}).get('data', '')
            if body_data:
                parsed['body'] = base64.urlsafe_b64decode(body_data).decode('utf-8')

        return parsed

    def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Mark message as read

        Args:
            message_id: Gmail message ID

        Returns:
            Updated message dict
        """
        if not self.service:
            if not self.authenticate():
                raise Exception("Gmail authentication failed")

        try:
            logger.info(f"Marking message as read: {message_id}")

            result = self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()

            return result

        except HttpError as error:
            logger.error(f"Gmail API error marking read: {error}")
            raise Exception(f"Failed to mark as read: {error}")

    def search_messages(
        self,
        from_email: Optional[str] = None,
        subject_contains: Optional[str] = None,
        body_contains: Optional[str] = None,
        unread_only: bool = True,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for messages matching criteria

        Args:
            from_email: Filter by sender
            subject_contains: Filter by subject keyword
            body_contains: Filter by body keyword
            unread_only: Only return unread messages
            max_results: Maximum messages to return

        Returns:
            List of parsed message dicts
        """
        # Build Gmail search query
        query_parts = []

        if from_email:
            query_parts.append(f'from:{from_email}')

        if subject_contains:
            query_parts.append(f'subject:{subject_contains}')

        if body_contains:
            query_parts.append(f'{body_contains}')

        if unread_only:
            query_parts.append('is:unread')

        query = ' '.join(query_parts)

        # List messages
        message_list = self.list_messages(query=query, max_results=max_results)

        # Get full details for each message
        parsed_messages = []
        for msg in message_list:
            try:
                full_msg = self.get_message(msg['id'])
                parsed = self.parse_message_body(full_msg)
                parsed_messages.append(parsed)
            except Exception as e:
                logger.error(f"Error parsing message {msg['id']}: {e}")

        return parsed_messages


# Singleton instance
_gmail_service: Optional[GmailService] = None


def get_gmail_service() -> GmailService:
    """Get or create Gmail service singleton"""
    global _gmail_service
    if _gmail_service is None:
        _gmail_service = GmailService()
    return _gmail_service


def is_gmail_configured() -> bool:
    """Check if Gmail is configured (credentials file exists)"""
    credentials_file = os.getenv('GMAIL_CREDENTIALS_FILE', 'credentials.json')
    return os.path.exists(credentials_file)
