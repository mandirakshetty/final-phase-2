# src/utils/parser.py (UPDATED VERSION)
import re
from datetime import datetime
from typing import List, Optional
from src.models.log_entry import LogEntry

class LogParser:
    @staticmethod
    def parse_line(line: str, zone: str, client: str, app: str, version: str) -> Optional[LogEntry]:
        """Parse your specific log format"""
        
        # Your log format: 2025-12-18T01:59:40.205469Z - ERROR - Component=LogIngestor - Code=E_DB_FAIL - Severity=HIGH - Message=... - App=Unigy
        
        pattern = r'(?P<timestamp>[\d\-T:.]+Z)\s+-\s+(?P<level>\w+)\s+-\s+(?P<full_message>.+)'
        
        match = re.match(pattern, line.strip())
        if not match:
            return None
        
        groups = match.groupdict()
        full_message = groups['full_message']
        
        # Extract components from the message part
        component_match = re.search(r'Component=([A-Za-z]+)', full_message)
        code_match = re.search(r'Code=([A-Z_]+)', full_message)
        message_match = re.search(r'Message=([^\-]+)', full_message)
        
        return LogEntry(
            timestamp=groups['timestamp'],
            log_level=groups['level'],
            component=component_match.group(1) if component_match else "Unknown",
            error_code=code_match.group(1) if code_match else None,
            message=message_match.group(1).strip() if message_match else full_message,
            zone=zone,
            client=client,
            app=app,
            version=version,
            raw_line=line.strip()
        )
    
    @staticmethod
    def extract_patterns(text: str) -> dict:
        """Extract patterns from your log text"""
        patterns = {
            'error_codes': re.findall(r'Code=([A-Z_]+)', text),
            'components': re.findall(r'Component=([A-Za-z]+)', text),
            'timestamps': re.findall(r'\d{4}-\d{2}-\d{2}T[\d:.]+Z', text),
            'trace_ids': re.findall(r'TraceID=([\w\-]+)', text),
            'severities': re.findall(r'Severity=([A-Z]+)', text),
            'retry_counts': re.findall(r'RetryCount=(\d+)', text),
            'messages': re.findall(r'Message=([^\-]+)', text)
        }
        return patterns