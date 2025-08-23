# core/src/memory_agent.py
# Minimal Memory Agent for basic memory operations
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from typing import Dict, Any, List, cast
from src.base_agent import BaseAgent


class MemoryAgent(BaseAgent):
    """
    Minimal memory agent for basic storage and retrieval operations.
    """
    
    def __init__(self):
        super().__init__(name="memory")
        self.version = "minimal-1.0"
        self._store: Dict[str, Any] = {}
    
    def run(self, input_data: Any) -> Dict[str, Any]:
        """
        Handle memory operations: save, recall, list, clear.
        """
        if not isinstance(input_data, dict):
            return {"error": "Input must be a dictionary with 'action' field", "success": False}

        input_data = cast(Dict[str, Any], input_data)  # Ensure input_data is typed
        action = str(input_data.get("action", "")).lower()

        if action == "save":
            return self._save_memory(input_data)
        elif action == "recall":
            return self._recall_memory(input_data)
        elif action == "list":
            return self._list_memories(input_data)
        elif action == "clear":
            return self._clear_memory(input_data)
        else:
            return {
                "error": f"Unknown action: {action}. Use: save, recall, list, clear",
                "success": False
            }
    
    def _save_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Save data to memory."""
        key = data.get("key")
        value = data.get("value")
        
        if not key:
            return {"error": "Missing 'key' for save operation", "success": False}
        if value is None:
            return {"error": "Missing 'value' for save operation", "success": False}
        
        # Store the value
        self._store[key] = {
            "value": value,
            "type": type(value).__name__,
            "saved_at": "now",
            "size": len(str(value))
        }
        
        return {
            "success": True,
            "action": "save",
            "key": key,
            "message": f"Saved {type(value).__name__} to '{key}'"
        }
    
    def _recall_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recall data from memory."""
        key = data.get("key")
        
        if not key:
            return {"error": "Missing 'key' for recall operation", "success": False}
        
        if key not in self._store:
            return {
                "success": False,
                "action": "recall", 
                "key": key,
                "message": f"No memory found for key '{key}'"
            }
        
        memory_item = self._store[key]
        
        return {
            "success": True,
            "action": "recall",
            "key": key,
            "value": memory_item["value"],
            "metadata": {
                "type": memory_item["type"],
                "saved_at": memory_item["saved_at"],
                "size": memory_item["size"]
            }
        }
    
    def _list_memories(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """List all stored memories."""
        memory_list: List[Dict[str, Any]] = []  # Explicitly type memory_list
        
        for key, item in self._store.items():
            memory_list.append({
                "key": key,
                "type": item["type"],
                "saved_at": item["saved_at"],
                "size": item["size"]
            })
        
        return {
            "success": True,
            "action": "list",
            "memories": memory_list,
            "total_count": len(memory_list)
        }
    
    def _clear_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clear memory (specific key or all)."""
        key = data.get("key")
        
        if key:
            # Clear specific key
            if key in self._store:
                del self._store[key]
                return {
                    "success": True,
                    "action": "clear",
                    "key": key,
                    "message": f"Cleared memory for '{key}'"
                }
            else:
                return {
                    "success": False,
                    "action": "clear",
                    "key": key,
                    "message": f"No memory found for key '{key}'"
                }
        else:
            # Clear all memories
            cleared_count = len(self._store)
            self._store.clear()
            return {
                "success": True,
                "action": "clear",
                "message": f"Cleared all {cleared_count} memories"
            }
    
    # Convenience methods for direct access
    def save(self, key: str, value: Any) -> bool:
        """Direct save method."""
        result = self._save_memory({"key": key, "value": value})
        return result["success"]
    
    def recall(self, key: str) -> Any:
        """Direct recall method."""
        result = self._recall_memory({"key": key})
        return result.get("value") if result["success"] else None
    
    def exists(self, key: str) -> bool:
        """Check if key exists in memory."""
        return key in self._store