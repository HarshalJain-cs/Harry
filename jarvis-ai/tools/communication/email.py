"""
JARVIS Email Client - Email reading and sending.

Provides email access using IMAP/SMTP with template support.
"""

import os
import json
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from tools.registry import tool, ToolResult, RiskLevel


@dataclass
class EmailAccount:
    """Email account configuration."""
    email: str
    password: str
    imap_server: str
    imap_port: int
    smtp_server: str
    smtp_port: int
    use_ssl: bool = True


@dataclass
class EmailMessage:
    """An email message."""
    id: str
    from_addr: str
    to_addr: str
    subject: str
    body: str
    date: datetime
    is_read: bool = False
    has_attachments: bool = False


# Common email provider configurations
EMAIL_PROVIDERS = {
    "gmail": EmailAccount(
        email="",
        password="",
        imap_server="imap.gmail.com",
        imap_port=993,
        smtp_server="smtp.gmail.com",
        smtp_port=587,
    ),
    "outlook": EmailAccount(
        email="",
        password="",
        imap_server="outlook.office365.com",
        imap_port=993,
        smtp_server="smtp.office365.com",
        smtp_port=587,
    ),
    "yahoo": EmailAccount(
        email="",
        password="",
        imap_server="imap.mail.yahoo.com",
        imap_port=993,
        smtp_server="smtp.mail.yahoo.com",
        smtp_port=587,
    ),
}


class EmailClient:
    """
    Email client for reading and sending emails.
    
    Features:
    - Read inbox and folders
    - Search emails
    - Send emails with templates
    - Support for common providers
    """
    
    def __init__(
        self,
        config_path: str = "./storage/email_config.json",
    ):
        """
        Initialize email client.
        
        Args:
            config_path: Path to email configuration file
        """
        self.config_path = config_path
        self.account: Optional[EmailAccount] = None
        self.imap: Optional[imaplib.IMAP4_SSL] = None
        self.templates: Dict[str, str] = {}
        
        self._load_config()
    
    def _load_config(self):
        """Load email configuration."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                
                if "account" in data:
                    self.account = EmailAccount(**data["account"])
                
                self.templates = data.get("templates", {})
            except Exception:
                pass
    
    def _save_config(self):
        """Save email configuration."""
        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "templates": self.templates,
        }
        
        if self.account:
            data["account"] = {
                "email": self.account.email,
                "password": "",  # Don't save password
                "imap_server": self.account.imap_server,
                "imap_port": self.account.imap_port,
                "smtp_server": self.account.smtp_server,
                "smtp_port": self.account.smtp_port,
                "use_ssl": self.account.use_ssl,
            }
        
        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def configure(
        self,
        email: str,
        password: str,
        provider: Optional[str] = None,
        custom_config: Optional[Dict] = None,
    ):
        """
        Configure email account.
        
        Args:
            email: Email address
            password: Password or app password
            provider: Provider name (gmail, outlook, yahoo)
            custom_config: Custom IMAP/SMTP settings
        """
        if provider and provider in EMAIL_PROVIDERS:
            base = EMAIL_PROVIDERS[provider]
            self.account = EmailAccount(
                email=email,
                password=password,
                imap_server=base.imap_server,
                imap_port=base.imap_port,
                smtp_server=base.smtp_server,
                smtp_port=base.smtp_port,
                use_ssl=base.use_ssl,
            )
        elif custom_config:
            self.account = EmailAccount(
                email=email,
                password=password,
                **custom_config,
            )
        else:
            raise ValueError("Must provide either provider or custom_config")
        
        self._save_config()
    
    def connect_imap(self):
        """Connect to IMAP server."""
        if not self.account:
            raise ValueError("Email account not configured")
        
        if self.account.use_ssl:
            self.imap = imaplib.IMAP4_SSL(
                self.account.imap_server,
                self.account.imap_port,
            )
        else:
            self.imap = imaplib.IMAP4(
                self.account.imap_server,
                self.account.imap_port,
            )
        
        self.imap.login(self.account.email, self.account.password)
    
    def disconnect(self):
        """Disconnect from IMAP server."""
        if self.imap:
            try:
                self.imap.logout()
            except:
                pass
            self.imap = None
    
    def get_folders(self) -> List[str]:
        """Get list of email folders."""
        if not self.imap:
            self.connect_imap()
        
        _, folders = self.imap.list()
        
        result = []
        for folder in folders:
            # Parse folder name
            if isinstance(folder, bytes):
                parts = folder.decode().split('"')
                if len(parts) >= 3:
                    result.append(parts[-2])
        
        return result
    
    def get_inbox(self, limit: int = 20) -> List[EmailMessage]:
        """Get recent inbox messages."""
        return self.get_messages("INBOX", limit)
    
    def get_messages(
        self,
        folder: str = "INBOX",
        limit: int = 20,
        unread_only: bool = False,
    ) -> List[EmailMessage]:
        """Get messages from folder."""
        if not self.imap:
            self.connect_imap()
        
        self.imap.select(folder)
        
        criteria = "UNSEEN" if unread_only else "ALL"
        _, message_ids = self.imap.search(None, criteria)
        
        ids = message_ids[0].split()
        ids = ids[-limit:] if len(ids) > limit else ids
        ids.reverse()  # Most recent first
        
        messages = []
        for msg_id in ids:
            _, msg_data = self.imap.fetch(msg_id, "(RFC822)")
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Decode subject
                    subject = msg["subject"] or ""
                    if isinstance(subject, bytes):
                        subject = subject.decode('utf-8', errors='replace')
                    
                    # Get body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                payload = part.get_payload(decode=True)
                                if payload:
                                    body = payload.decode('utf-8', errors='replace')
                                    break
                    else:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            body = payload.decode('utf-8', errors='replace')
                    
                    # Parse date
                    date_str = msg.get("date", "")
                    try:
                        date = email.utils.parsedate_to_datetime(date_str)
                    except:
                        date = datetime.now()
                    
                    messages.append(EmailMessage(
                        id=msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                        from_addr=msg.get("from", ""),
                        to_addr=msg.get("to", ""),
                        subject=subject,
                        body=body[:2000],  # Truncate
                        date=date,
                    ))
        
        return messages
    
    def search_messages(self, query: str, folder: str = "INBOX") -> List[EmailMessage]:
        """Search messages by subject or sender."""
        if not self.imap:
            self.connect_imap()
        
        self.imap.select(folder)
        
        # Search by subject and from
        _, subject_ids = self.imap.search(None, f'(SUBJECT "{query}")')
        _, from_ids = self.imap.search(None, f'(FROM "{query}")')
        
        # Combine results
        all_ids = set(subject_ids[0].split() + from_ids[0].split())
        
        messages = []
        for msg_id in list(all_ids)[:20]:
            _, msg_data = self.imap.fetch(msg_id, "(RFC822)")
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    messages.append(EmailMessage(
                        id=msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                        from_addr=msg.get("from", ""),
                        to_addr=msg.get("to", ""),
                        subject=msg["subject"] or "",
                        body="",  # Don't fetch body for search
                        date=datetime.now(),
                    ))
        
        return messages
    
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool = False,
    ) -> bool:
        """
        Send an email.
        
        Args:
            to: Recipient email
            subject: Email subject
            body: Email body
            html: Whether body is HTML
        """
        if not self.account:
            raise ValueError("Email account not configured")
        
        msg = MIMEMultipart()
        msg["From"] = self.account.email
        msg["To"] = to
        msg["Subject"] = subject
        
        content_type = "html" if html else "plain"
        msg.attach(MIMEText(body, content_type))
        
        with smtplib.SMTP(self.account.smtp_server, self.account.smtp_port) as server:
            server.starttls()
            server.login(self.account.email, self.account.password)
            server.send_message(msg)
        
        return True
    
    def add_template(self, name: str, template: str):
        """Add an email template."""
        self.templates[name] = template
        self._save_config()
    
    def send_from_template(
        self,
        template_name: str,
        to: str,
        subject: str,
        variables: Dict[str, str],
    ) -> bool:
        """Send email using a template."""
        if template_name not in self.templates:
            raise ValueError(f"Template not found: {template_name}")
        
        body = self.templates[template_name]
        
        # Replace variables
        for key, value in variables.items():
            body = body.replace(f"{{{key}}}", value)
        
        return self.send_email(to, subject, body)


# Tool registrations
@tool(
    name="check_email",
    description="Check for new emails in inbox",
    category="communication",
    examples=["check my email", "any new emails?"],
)
def check_email(limit: int = 10) -> ToolResult:
    """Check inbox for emails."""
    try:
        client = EmailClient()
        
        if not client.account:
            return ToolResult(
                success=False,
                error="Email not configured. Use 'configure_email' first.",
            )
        
        messages = client.get_inbox(limit)
        client.disconnect()
        
        emails = [
            {
                "from": m.from_addr[:40],
                "subject": m.subject[:50],
                "date": m.date.strftime("%Y-%m-%d %H:%M"),
            }
            for m in messages
        ]
        
        return ToolResult(success=True, output=emails)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="search_email",
    description="Search emails by subject or sender",
    category="communication",
)
def search_email(query: str) -> ToolResult:
    """Search emails."""
    try:
        client = EmailClient()
        
        if not client.account:
            return ToolResult(
                success=False,
                error="Email not configured",
            )
        
        messages = client.search_messages(query)
        client.disconnect()
        
        emails = [
            {
                "from": m.from_addr[:40],
                "subject": m.subject[:50],
            }
            for m in messages
        ]
        
        return ToolResult(success=True, output=emails)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="send_email",
    description="Send an email",
    risk_level=RiskLevel.MEDIUM,
    category="communication",
    examples=["send email to john@example.com about meeting"],
)
def send_email(to: str, subject: str, body: str) -> ToolResult:
    """Send email."""
    try:
        client = EmailClient()
        
        if not client.account:
            return ToolResult(
                success=False,
                error="Email not configured",
            )
        
        client.send_email(to, subject, body)
        
        return ToolResult(
            success=True,
            output=f"Email sent to {to}",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="configure_email",
    description="Configure email account",
    risk_level=RiskLevel.HIGH,
    category="communication",
)
def configure_email(
    email_addr: str,
    password: str,
    provider: str = "gmail",
) -> ToolResult:
    """Configure email account."""
    try:
        client = EmailClient()
        client.configure(email_addr, password, provider)
        
        # Test connection
        client.connect_imap()
        client.disconnect()
        
        return ToolResult(
            success=True,
            output=f"Email configured: {email_addr} ({provider})",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Email Client...")
    print("Note: Email requires valid credentials to test")
    
    client = EmailClient(config_path="./test_email_config.json")
    
    # Test templates
    client.add_template("greeting", "Hello {name}!\n\n{message}\n\nBest regards,\n{sender}")
    print("Added template: greeting")
    
    print(f"Templates: {list(client.templates.keys())}")
    
    # Cleanup
    if os.path.exists("./test_email_config.json"):
        os.remove("./test_email_config.json")
    
    print("\nTests complete!")
