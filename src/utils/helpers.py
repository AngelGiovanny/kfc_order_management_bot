import re
import ipaddress
from datetime import datetime
from typing import Optional

def is_valid_guid(guid: str) -> bool:
    """Validate GUID format"""
    pattern = re.compile(
        r'^[{(]?([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})[)}]?$'
    )
    return bool(pattern.match(guid))

def is_valid_ip(ip: str) -> bool:
    """Validate IP address"""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def format_datetime(dt: datetime) -> str:
    """Format datetime for display"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def safe_int(value, default=0):
    """Safely convert to int"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to maximum length"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def build_server_name(store_code: str) -> str:
    """Build server name from store code"""
    store_number = ''.join(filter(str.isdigit, store_code))
    return f"10.101.{store_number}.20"