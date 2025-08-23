# core/src/utils.py
# Minimal utility functions for OrbitSuite core
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import json
import time
from typing import Any, Dict, List, Optional


from typing import Optional


def format_timestamp(timestamp: Optional[float] = None) -> str:
    """Format timestamp for logging."""
    if timestamp is None:
        timestamp = time.time()
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))


def safe_json_dumps(data: Any, indent: int = 2) -> str:
    """Safely serialize data to JSON."""
    try:
        return json.dumps(data, indent=indent, default=str)
    except Exception:
        return str(data)


def safe_json_loads(data: str) -> Any:
    """Safely deserialize JSON data."""
    try:
        return json.loads(data)
    except Exception:
        return data


def get_bool(value: Optional[str], default: bool = False) -> bool:
    """Parse common boolean env-style strings."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def is_verbose() -> bool:
    """Return True if verbose logging is enabled via ORBITSUITE_VERBOSE."""
    return get_bool(os.getenv("ORBITSUITE_VERBOSE"), False)


def load_dotenv(dotenv_path: Optional[str] = None, override: bool = False) -> Dict[str, str]:
    """Load environment variables from a .env file without external deps.

    - dotenv_path: explicit path to .env; if None, tries multiple locations:
        1) ORBITSUITE_DOTENV env var, if set
        2) ./src/.env relative to this utils module (source run)
        3) <_MEIPASS>/src/.env if running from PyInstaller onefile
        4) CWD variants: ./src/.env then ./.env
    - override: when True, overrides existing env vars; otherwise preserves existing
    Returns a dict of loaded key/value pairs.
    """
    loaded: Dict[str, str] = {}
    # Determine candidate paths
    candidates: list[str] = []
    if dotenv_path:
        candidates.append(dotenv_path)
    env_path = os.getenv("ORBITSUITE_DOTENV")
    if env_path:
        candidates.append(env_path)
    # 2) relative to this file (source checkout)
    candidates.append(os.path.join(os.path.dirname(__file__), '.env'))
    # 3) PyInstaller _MEIPASS bundle path
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(os.path.join(meipass, 'src', '.env'))
    # 4) CWD variants
    candidates.append(os.path.join(os.getcwd(), 'src', '.env'))
    candidates.append(os.path.join(os.getcwd(), '.env'))

    # Pick first existing path
    dotenv_path_final: Optional[str] = next((p for p in candidates if os.path.exists(p)), None)
    if not dotenv_path_final:
        return loaded

    try:
        with open(dotenv_path_final, 'r', encoding='utf-8') as f:
            for raw in f.read().splitlines():
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                if line.lower().startswith('export '):
                    line = line[7:].strip()
                if '=' not in line:
                    continue
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and (override or key not in os.environ):
                    os.environ[key] = value
                    loaded[key] = value
    except Exception:
        # fail silently; caller can inspect returned dict
        pass
    return loaded


def truncate_string(text: str, max_length: int = 100) -> str:
    """Truncate string to specified length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def extract_keywords(text: str) -> List[str]:
    """Extract basic keywords from text."""
    if not text:
        return []
    
    # Simple keyword extraction
    words = text.lower().split()
    
    # Filter out common stop words
    stop_words = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
        "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
        "to", "was", "were", "will", "with", "this", "but", "they",
        "have", "had", "what", "said", "each", "which", "their", "time",
        "if", "up", "out", "many", "then", "them", "these", "so", "some"
    }
    
    keywords = [word for word in words if word not in stop_words and len(word) > 2]
    
    # Return unique keywords, limited to top 10
    return list(dict.fromkeys(keywords))[:10]


def validate_agent_input(input_data: Any, required_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """Validate agent input data."""
    errors: List[str] = []
    warnings: List[str] = []
    validation_result: Dict[str, Any] = {"valid": True, "errors": errors, "warnings": warnings}
    
    if input_data is None:
        validation_result["valid"] = False
        errors.append("Input data is None")
        return validation_result
    
    if required_fields:
        if not isinstance(input_data, dict):
            validation_result["valid"] = False
            errors.append("Input must be a dictionary when required fields are specified")
            return validation_result
        
        for field in required_fields:
            if field not in input_data:
                validation_result["valid"] = False
                errors.append(f"Required field '{field}' is missing")
            elif input_data[field] is None:
                warnings.append(f"Required field '{field}' is None")
    
    return validation_result


def create_task_id(prefix: str = "task") -> str:
    """Create a unique task ID."""
    timestamp = int(time.time() * 1000)  # milliseconds
    return f"{prefix}_{timestamp}"


def merge_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge multiple agent results into a single result."""
    if not results:
        return {"success": False, "error": "No results to merge"}
    
    merged: Dict[str, Any] = {
        "success": all(r.get("success", False) for r in results),
        "total_results": len(results),
        "individual_results": results
    }
    
    # Collect all errors
    errors: List[str] = []
    for result in results:
        if "error" in result:
            errors.append(result["error"])
    
    if errors:
        merged["errors"] = errors
    
    # Collect successful results
    successful_results = [r for r in results if r.get("success", False)]
    failed_results = [r for r in results if not r.get("success", False)]
    
    merged["successful_count"] = len(successful_results)
    merged["failed_count"] = len(failed_results)
    
    return merged


class SimpleLogger:
    """Simple logging utility for core operations."""
    
    def __init__(self, name: str = "CoreLogger"):
        self.name = name
        self.logs: List[Dict[str, Any]] = []
    
    def log(self, level: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Log a message with optional data."""
        log_entry: Dict[str, Any] = {
            "timestamp": time.time(),
            "level": level.upper(),
            "message": message,
            "logger": self.name
        }
        
        if data:
            log_entry["data"] = data
        
        self.logs.append(log_entry)
        
        # Print to console for immediate feedback
        print(f"[{format_timestamp()}] {level.upper()}: {message}")
        
        # Keep only last 1000 entries
        if len(self.logs) > 1000:
            self.logs = self.logs[-1000:]
    
    def info(self, message: str, data: Optional[Dict[str, Any]] = None):
        """Log info message."""
        self.log("info", message, data)
    
    def error(self, message: str, data: Optional[Dict[str, Any]] = None):
        """Log error message."""
        self.log("error", message, data)
    
    def warning(self, message: str, data: Optional[Dict[str, Any]] = None):
        """Log warning message."""
        self.log("warning", message, data)
    
    def get_logs(self, level: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent logs, optionally filtered by level."""
        logs = self.logs
        
        if level:
            logs = [log for log in logs if log["level"] == level.upper()]
        
        return logs[-limit:]
    
    def clear_logs(self):
        """Clear all logs."""
        self.logs = []