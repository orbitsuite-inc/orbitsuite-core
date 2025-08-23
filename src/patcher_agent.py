# core/src/patcher_agent.py
# Minimal Patcher Agent for basic code patching and repair
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import re
from typing import Dict, Any, List, Union
from src.base_agent import BaseAgent


class PatcherAgent(BaseAgent):
    """
    Minimal patching agent for basic code repair and modification.
    """
    
    def __init__(self):
        super().__init__(name="patcher")
        self.version = "minimal-1.0"
    
    def run(self, input_data: Dict[str, Union[str, List[str]]]) -> Dict[str, Any]:
        """
        Apply patches or fixes to code.
        """
        code = input_data.get("code", "")
        if not isinstance(code, str):
            return {"error": "Invalid type for 'code'. Expected a string.", "success": False}

        issues = input_data.get("issues", [])
        if not isinstance(issues, list):
            return {"error": "Invalid type for 'issues'. Expected a list of strings.", "success": False}
        # ...existing code...
        patch_type = input_data.get("type", "auto")
        if not isinstance(patch_type, str):
            return {"error": "Invalid type for 'type'. Expected a string.", "success": False}

        # Apply patches based on type
        if patch_type == "syntax":
            result = self._fix_syntax_issues(code, issues)
        elif patch_type == "style":
            result = self._fix_style_issues(code)
        elif patch_type == "auto":
            result = self._auto_patch(code, issues)
        else:
            return {"error": f"Unknown patch type: {patch_type}", "success": False}
        # Write artifact summary (best-effort)
        try:
            from pathlib import Path
            import json, time
            out_dir = Path.cwd() / "output" / "patches"
            out_dir.mkdir(parents=True, exist_ok=True)
            stem = f"patch_{int(time.time())}"
            with open(out_dir / f"{stem}.json", "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            result["artifact_path"] = str(out_dir / f"{stem}.json")
        except Exception:
            pass
        return result
    
    def _fix_syntax_issues(self, code: str, issues: List[str]) -> Dict[str, Any]:
        """Fix basic syntax issues."""
        original_code = code
        patched_code = code
        fixes_applied: List[str] = []
        
        # Fix common indentation issues
        if any("indentation" in issue.lower() for issue in issues):
            patched_code = self._fix_indentation(patched_code)
            fixes_applied.append("Fixed indentation")
        
        # Fix missing colons
        if any("colon" in issue.lower() for issue in issues):
            patched_code = self._fix_missing_colons(patched_code)
            fixes_applied.append("Added missing colons")
        
        # Fix common syntax errors
        patched_code = self._fix_common_syntax(patched_code)
        
        return {
            "success": True,
            "original_code": original_code,
            "patched_code": patched_code,
            "fixes_applied": fixes_applied,
            "patch_type": "syntax"
        }
    
    def _fix_style_issues(self, code: str) -> Dict[str, Any]:
        """Fix basic style issues."""
        original_code = code
        patched_code = code
        fixes_applied: List[str] = []
        
        # Fix spacing around operators
        code = code.replace("=", " = ").replace("+", " + ").replace("-", " - ")
        fixes_applied.append("Fixed operator spacing")
        
        # Fix trailing whitespace
        lines = patched_code.split('\n')
        lines = [line.rstrip() for line in lines]
        patched_code = '\n'.join(lines)
        fixes_applied.append("Removed trailing whitespace")
        
        # Fix multiple blank lines
        patched_code = re.sub(r'\n\n\n+', '\n\n', patched_code)
        fixes_applied.append("Fixed multiple blank lines")
        
        return {
            "success": True,
            "original_code": original_code,
            "patched_code": patched_code,
            "fixes_applied": fixes_applied,
            "patch_type": "style"
        }
    
    def _auto_patch(self, code: str, issues: List[str]) -> Dict[str, Any]:
        """Automatically detect and fix common issues."""
        original_code = code
        patched_code = code
        fixes_applied: List[str] = []
        
        # Detect and fix various issues
        
        # 1. Fix incomplete functions
        if "TODO" in patched_code or "pass" in patched_code:
            patched_code = self._fix_incomplete_functions(patched_code)
            fixes_applied.append("Added basic function implementations")
        
        # 2. Fix missing imports
        patched_code = self._fix_missing_imports(patched_code)
        if "import" in patched_code and "import" not in original_code:
            fixes_applied.append("Added missing imports")
        
        # 3. Fix basic syntax issues
        patched_code = self._fix_common_syntax(patched_code)
        fixes_applied.append("Fixed basic syntax issues")
        
        # 4. Fix style issues
        style_result = self._fix_style_issues(patched_code)
        patched_code = style_result["patched_code"]
        fixes_applied.extend(style_result["fixes_applied"])
        
        return {
            "success": True,
            "original_code": original_code,
            "patched_code": patched_code,
            "fixes_applied": fixes_applied,
            "patch_type": "auto",
            "issues_detected": len(fixes_applied)
        }
    
    def _fix_indentation(self, code: str) -> str:
        """Fix basic indentation issues."""
        lines = code.split('\n')
        fixed_lines: List[str] = []
        indent_level = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                fixed_lines.append('')
                continue
            
            # Decrease indent for certain keywords
            if stripped.startswith(('elif', 'else', 'except', 'finally')):
                indent_level = max(0, indent_level - 1)
            
            # Add proper indentation
            fixed_lines.append('    ' * indent_level + stripped)
            
            # Increase indent after colon
            if stripped.endswith(':'):
                indent_level += 1
        
        return '\n'.join(fixed_lines)
    
    def _fix_missing_colons(self, code: str) -> str:
        """Add missing colons after control statements."""
        # Add colons after if, for, while, def, class statements
        patterns = [
            (r'(if\s+.+)(?<!:)$', r'\1:'),
            (r'(for\s+.+)(?<!:)$', r'\1:'),
            (r'(while\s+.+)(?<!:)$', r'\1:'),
            (r'(def\s+\w+\([^)]*\))(?<!:)$', r'\1:'),
            (r'(class\s+\w+(?:\([^)]*\))?)(?<!:)$', r'\1:'),
        ]
        
        for pattern, replacement in patterns:
            code = re.sub(pattern, replacement, code, flags=re.MULTILINE)
        
        return code
    
    def _fix_common_syntax(self, code: str) -> str:
        """Fix common syntax issues."""
        # Fix print statements (Python 3)
        code = re.sub(r'print\s+([^(].+)$', r'print(\1)', code, flags=re.MULTILINE)
        
        # Fix string formatting
        code = code.replace("%s", "{}")
        
        return code
    
    def _fix_incomplete_functions(self, code: str) -> str:
        """Add basic implementations to incomplete functions."""
        # Replace TODO comments with basic return statements
        code = re.sub(r'#\s*TODO.*', 'return None  # TODO: Implement', code)
        
        # Replace bare pass statements in functions with return statements
        lines = code.split('\n')
        in_function = False
        fixed_lines: List[str] = []
        
        for line in lines:
            if line.strip().startswith('def '):
                in_function = True
                fixed_lines.append(line)
                continue
            if line.strip() == 'pass' and in_function:
                fixed_lines.append(line.replace('pass', 'return None'))
                continue
            # Detect dedent to end function
            if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                in_function = False
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _fix_missing_imports(self, code: str) -> str:
        """Add basic missing imports."""
        imports_to_add: List[str] = []
        
        # Check for common missing imports
        if 'json.' in code and 'import json' not in code:
            imports_to_add.append('import json')
        if 'os.' in code and 'import os' not in code:
            imports_to_add.append('import os')
        if 'sys.' in code and 'import sys' not in code:
            imports_to_add.append('import sys')
        if 'datetime' in code and 'import datetime' not in code and 'from datetime' not in code:
            imports_to_add.append('from datetime import datetime')
        
        if imports_to_add:
            imports_section = '\n'.join(imports_to_add) + '\n\n'
            code = imports_section + code
        
        return code