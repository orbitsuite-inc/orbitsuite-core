# agents/task_linguist_core.py
# 🧠 ORBITSUITE TASK LINGUIST CORE
# Purpose: Open core natural language processing for OrbitSuite task creation.
# Provides basic intent recognition, entity extraction, and task parsing for open source users.
# © 2025 OrbitSuite, Inc. All rights reserved.
# License: Open Core - Basic functionality available to all users

import uuid
import re
import hashlib
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
from .base_agent import BaseAgent  # local core base
try:
    from .utils import is_verbose as _core_is_verbose  # type: ignore
except Exception:
    def _core_is_verbose() -> bool:  # fallback always False
        return False

def log_step(message: str) -> None:
    """Lightweight logging helper for core mode avoiding external deps."""
    if _core_is_verbose():
        print(f"[linguist-core] {message}")

# Constants
TEXT_INPUT_REQUIRED_ERROR = "Text input is required"
CORE_VERSION = "1.0.0-core"


@dataclass
class CoreTaskIntent:
    """
    Core task intent representation for open source users.
    Provides essential intent classification with confidence scoring.
    """
    intent_type: str
    confidence: float
    entities: Dict[str, Any]
    agent_target: Optional[str] = None
    priority: int = 5
    complexity: str = "medium"  # low, medium, high
    estimated_time: Optional[int] = None  # seconds


class TaskLinguistCore(BaseAgent):
    """
    Core natural language processor for OrbitSuite task creation.
    
    Open Core Features:
    - Pattern-based intent recognition
    - Basic entity extraction
    - Simple complexity assessment  
    - Agent capability mapping
    - Task structure generation
    - Legacy compatibility
    
    This is the open source foundation that provides essential NLP functionality
    for basic OrbitSuite task creation and agent coordination. Advanced features
    like AI-powered decomposition, complex analytics, and enterprise integrations
    are available in the full TaskLinguist agent.
    """
    
    def __init__(self):
        """Initialize the core task linguist with open source functionality."""
        super().__init__(name="task_linguist_core")
        self.description = "Open core natural language processing for basic task creation"
        self.version = CORE_VERSION
        
        # Core intent recognition patterns - open source patterns
        self.core_intent_patterns = {
            "code_generation": [
                r"(write|create|generate|build).*?(code|function|class|script|program)",
                r"implement.*",
                r"develop.*",
                r"program.*"
            ],
            "testing": [
                r"test.*",
                r"run.*test",
                r"verify.*",
                r"check.*",
                r"validate.*"
            ],
            "documentation": [
                r"(document|docs|documentation).*",
                r"explain.*",
                r"describe.*",
                r"create.*documentation"
            ],
            "analysis": [
                r"(analyze|examine|investigate|review).*",
                r"find.*(bugs|issues|problems)",
                r"(scan|search|look).*"
            ],
            "security": [
                r"(secure|protect|guard).*",
                r".*(security|vulnerabilities|audit).*",
                r"check.*(security|vulnerabilities)"
            ],
            "deployment": [
                r"(deploy|release|publish).*",
                r"(setup|configure|install).*",
                r"(start|launch|run).*(server|service|application)"
            ],
            "monitoring": [
                r"(monitor|watch|track).*",
                r"(observe|log|record).*",
                r"check.*(status|health|performance)"
            ]
        }
        
        # Core agent capability mapping - basic open source agents
        self.core_agent_capabilities = {
            "engineer": ["architecture", "design", "planning", "analysis"],
            "codegen": ["code_generation", "implementation", "refactoring"],
            "tester": ["testing", "validation", "quality_assurance"],
            "patcher": ["fixes", "patches", "debugging", "maintenance"]
        }
        
        # Core complexity indicators for open source assessment
        self.core_complexity_indicators = {
            "high": ["complex", "advanced", "enterprise", "production", "scalable", "distributed"],
            "medium": ["moderate", "standard", "typical", "regular", "normal"],
            "low": ["simple", "basic", "quick", "easy", "minimal", "small"]
        }
        
        # Basic caching for performance - limited to core functionality
        self.core_intent_cache: Dict[str, CoreTaskIntent] = {}
        
        # Optional conductor registration for open core
        self._register_with_conductor_if_available()
    
    def _register_with_conductor_if_available(self) -> None:
        """No-op in core mode (conductor not bundled)."""
        return None
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute core task linguist commands.
        
        Supported commands:
        - parse: Basic natural language parsing
        - parse_prompt_to_task: Legacy compatibility
        - analyze_intent: Core intent analysis
        - suggest_agent: Basic agent suggestion
        - validate_task: Basic task validation
        - status: Core status information
        - clear_cache: Clear intent cache
        """
        command = input_data.get("command", "parse")
        
        if command == "parse":
            return self._parse_natural_language_core(input_data)
        elif command == "parse_prompt_to_task":
            # Legacy compatibility for CLI/open core users
            prompt = input_data.get("prompt", "")
            result = self.parse_prompt_to_task(prompt)
            return {"success": True, "task": result, "core_mode": True}
        elif command == "analyze_intent":
            return self._analyze_intent_core(input_data)
        elif command == "suggest_agent":
            return self._suggest_best_agent_core(input_data)
        elif command == "validate_task":
            return self._validate_task_structure_core(input_data)
        elif command == "status":
            return self._get_core_status()
        elif command == "clear_cache":
            return self._clear_core_cache()
        else:
            return {
                "success": False, 
                "error": f"Unknown core linguist command: {command}",
                "available_commands": ["parse", "parse_prompt_to_task", "analyze_intent", "suggest_agent", "validate_task", "status", "clear_cache"]
            }
    
    def _parse_natural_language_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core natural language parsing with basic intent recognition.
        
        Provides essential functionality for open source users without
        advanced AI decomposition or enterprise features.
        """
        try:
            text = input_data.get("text", "")
            target_agent = input_data.get("target_agent")
            
            if not text:
                return {"success": False, "error": TEXT_INPUT_REQUIRED_ERROR}
            
            # Analyze intent using core patterns
            intent_result = self._analyze_intent_core({"text": text})
            if not intent_result["success"]:
                return intent_result
            
            intent = CoreTaskIntent(**intent_result["intent"])
            
            # Create basic task structure
            base_task = self._create_core_task(text, intent, target_agent)
            
            # Generate core response
            response = {
                "success": True,
                "core_mode": True,
                "version": self.version,
                "original_text": text,
                "intent": {
                    "type": intent.intent_type,
                    "confidence": intent.confidence,
                    "complexity": intent.complexity,
                    "entities": intent.entities,
                    "agent_target": intent.agent_target,
                    "priority": intent.priority
                },
                "task": base_task,
                "note": "Core functionality - upgrade to TaskLinguist Pro for advanced features"
            }
            
            log_step(f"TaskLinguistCore parsed: {text} -> {intent.intent_type} (confidence: {intent.confidence:.2f})")
            
            return response
        
        except Exception as e:
            return {"success": False, "error": f"Core natural language parsing failed: {e}"}
    
    def _analyze_intent_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core intent analysis using pattern matching and basic entity extraction.
        """
        try:
            text = input_data.get("text", "")
            
            if not text:
                return {"success": False, "error": TEXT_INPUT_REQUIRED_ERROR}
            
            # Check basic cache first
            cache_key = hashlib.md5(text.encode()).hexdigest()
            if cache_key in self.core_intent_cache:
                cached_intent = self.core_intent_cache[cache_key]
                return {
                    "success": True,
                    "intent": {
                        "intent_type": cached_intent.intent_type,
                        "confidence": cached_intent.confidence,
                        "entities": cached_intent.entities,
                        "agent_target": cached_intent.agent_target,
                        "priority": cached_intent.priority,
                        "complexity": cached_intent.complexity,
                        "estimated_time": cached_intent.estimated_time
                    },
                    "cached": True,
                    "core_mode": True
                }
            
            # Core pattern-based intent recognition
            intent_scores: Dict[str, float] = {}
            for intent_type, patterns in self.core_intent_patterns.items():
                score = 0
                for pattern in patterns:
                    if re.search(pattern, text.lower()):
                        score += 1
                if score > 0:
                    intent_scores[intent_type] = score / len(patterns)
            
            # Determine primary intent
            if intent_scores:
                primary_intent = max(intent_scores.keys(), key=lambda x: intent_scores[x])
                confidence = intent_scores[primary_intent]
            else:
                primary_intent = "general"
                confidence = 0.5
            
            # Extract basic entities
            entities = self._extract_core_entities(text)
            
            # Assess complexity using core indicators
            complexity = self._assess_core_complexity(text)
            
            # Suggest target agent using core capabilities
            agent_target = self._suggest_core_agent_for_intent(primary_intent, entities)
            
            # Estimate priority using core logic
            priority = self._estimate_core_priority(text, primary_intent)
            
            # Estimate execution time using core calculations
            estimated_time = self._estimate_core_execution_time(complexity, primary_intent)
            
            # Create core intent object
            intent = CoreTaskIntent(
                intent_type=primary_intent,
                confidence=confidence,
                entities=entities,
                agent_target=agent_target,
                priority=priority,
                complexity=complexity,
                estimated_time=estimated_time
            )
            
            # Cache the result for performance
            self.core_intent_cache[cache_key] = intent
            
            return {
                "success": True,
                "intent": {
                    "intent_type": intent.intent_type,
                    "confidence": intent.confidence,
                    "entities": intent.entities,
                    "agent_target": intent.agent_target,
                    "priority": intent.priority,
                    "complexity": intent.complexity,
                    "estimated_time": intent.estimated_time
                },
                "cached": False,
                "core_mode": True
            }
        
        except Exception as e:
            return {"success": False, "error": f"Core intent analysis failed: {e}"}
    
    def _extract_core_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract entities from text using basic pattern matching.
        Core functionality for open source users.
        """
        entities = {}
        
        # File patterns - basic detection
        file_patterns = r'\b\w+\.\w+\b'
        files = re.findall(file_patterns, text)
        if files:
            entities["files"] = files
        
        # Programming languages - core set
        core_languages = ["python", "javascript", "java", "c++", "c#", "go", "rust", "typescript"]
        found_languages = [lang for lang in core_languages if lang.lower() in text.lower()]
        if found_languages:
            entities["languages"] = found_languages
        
        # Technologies/frameworks - basic set
        core_technologies = ["react", "vue", "angular", "django", "flask", "express", "spring", "docker"]
        found_tech = [tech for tech in core_technologies if tech.lower() in text.lower()]
        if found_tech:
            entities["technologies"] = found_tech
        
        # Numbers (for priorities, quantities, etc.)
        numbers = re.findall(r'\b\d+\b', text)
        if numbers:
            entities["numbers"] = [int(n) for n in numbers]
        
        # Action verbs - core set
        core_action_verbs = ["create", "build", "test", "deploy", "fix", "update", "delete", "analyze"]
        found_actions = [verb for verb in core_action_verbs if verb.lower() in text.lower()]
        if found_actions:
            entities["actions"] = found_actions
        
        return entities
    
    def _assess_core_complexity(self, text: str) -> str:
        """
        Assess task complexity using core indicators.
        Basic complexity assessment for open source users.
        """
        text_lower = text.lower()
        
        # Check for core complexity indicators
        for complexity, indicators in self.core_complexity_indicators.items():
            if any(indicator in text_lower for indicator in indicators):
                return complexity
        
        # Length-based assessment fallback
        word_count = len(text.split())
        if word_count > 50:
            return "high"
        elif word_count > 20:
            return "medium"
        else:
            return "low"
    
    def _suggest_core_agent_for_intent(self, intent_type: str, entities: Dict[str, Any]) -> Optional[str]:
        """
        Suggest the best core agent for handling this intent.
        Uses basic agent capability mapping for open source.
        """
        # Core intent to agent mapping
        core_intent_to_agent = {
            "code_generation": "codegen",
            "testing": "tester",
            "documentation": "engineer",  # Basic documentation via engineer
            "analysis": "engineer",
            "security": "engineer",  # Basic security via engineer
            "deployment": "engineer",
            "monitoring": "engineer"
        }
        
        if intent_type in core_intent_to_agent:
            return core_intent_to_agent[intent_type]
        
        # Check entities for specific technologies
        if "files" in entities:
            return "engineer"  # Basic file processing
        
        if "languages" in entities:
            return "codegen"  # Code generation
        
        # Default to engineer for general tasks
        return "engineer"
    
    def _estimate_core_priority(self, text: str, intent_type: str) -> int:
        """
        Estimate task priority using core logic.
        Basic priority estimation for open source users.
        """
        text_lower = text.lower()
        
        # High priority indicators
        urgent_words = ["urgent", "critical", "emergency", "asap", "immediately", "now"]
        if any(word in text_lower for word in urgent_words):
            return 9
        
        # Medium-high priority
        important_words = ["important", "high", "priority", "soon", "quickly"]
        if any(word in text_lower for word in important_words):
            return 7
        
        # Low priority indicators
        low_words = ["later", "when possible", "low priority", "optional"]
        if any(word in text_lower for word in low_words):
            return 3
        
        # Intent-based priority for core intents
        high_priority_intents = ["security", "testing"]
        if intent_type in high_priority_intents:
            return 6
        
        return 5  # Default medium priority
    
    def _estimate_core_execution_time(self, complexity: str, intent_type: str) -> int:
        """
        Estimate execution time using core calculations.
        Basic time estimation for open source users.
        """
        # Core base times (more conservative estimates)
        core_base_times = {
            "code_generation": 240,  # 4 minutes
            "testing": 180,          # 3 minutes
            "documentation": 300,    # 5 minutes
            "analysis": 120,         # 2 minutes
            "security": 180,         # 3 minutes
            "deployment": 300,       # 5 minutes
            "monitoring": 60         # 1 minute
        }
        
        base_time = core_base_times.get(intent_type, 180)
        
        # Core complexity multipliers
        complexity_multipliers = {
            "low": 0.7,
            "medium": 1.0,
            "high": 1.5  # Less aggressive than enterprise version
        }
        
        return int(base_time * complexity_multipliers.get(complexity, 1.0))
    
    def _create_core_task(self, text: str, intent: CoreTaskIntent, target_agent: Optional[str]) -> Dict[str, Any]:
        """
        Create basic task structure from parsed intent.
        Core task generation for open source users.
        """
        agent_id = target_agent or intent.agent_target or "engineer"
        
        # Generate core function name
        function_name = self._generate_core_function_name(intent.intent_type, intent.entities)
        
        # Map core intent to orchestrator task type naming convention
        intent_map = {
            "code_generation": "codegen",
            "testing": "testing",
            "analysis": "analysis",
            "security": "security",
            "deployment": "deployment",
            "monitoring": "monitoring",
            "documentation": "documentation",
        }
        task_type = intent_map.get(intent.intent_type, intent.intent_type or "general")

        # Orchestrator expects 'agent_target'; keep legacy 'agent_id' for compatibility
        agent_target = agent_id

        # Provide a stable short id plus full UUID alias 'task_id'
        short_id = uuid.uuid4().hex[:8]
        full_id = f"core_task_{short_id}"

        # Create core task structure
        task = {
            # Legacy / internal id
            "id": full_id,
            # Orchestrator-compatible identifiers
            "task_id": full_id,
            "type": task_type,
            "description": text,
            "agent_target": agent_target,
            "priority": intent.priority,
            "depends_on": [],
            "agent_id": agent_id,  # maintain original field
            "function": function_name,
            "arguments": {
                "description": text,
                "intent_type": intent.intent_type,
                "entities": intent.entities,
                "complexity": intent.complexity,
                "estimated_time": intent.estimated_time,
                "core_mode": True
            },
            # Orchestrator may look for generic 'input'
            "input": text,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "confidence": intent.confidence,
                "original_text": text,
                "linguist_version": self.version,
                "core_edition": True
            }
        }
        
        return task
    
    def _generate_core_function_name(self, intent_type: str, entities: Dict[str, Any]) -> str:
        """
        Generate appropriate function name using core mapping.
        Basic function name generation for open source users.
        """
        core_function_mapping = {
            "code_generation": "generate_code",
            "testing": "run_tests",
            "documentation": "create_documentation",
            "analysis": "analyze_code",
            "security": "basic_security_check",
            "deployment": "deploy_application",
            "monitoring": "monitor_system"
        }
        
        base_function = core_function_mapping.get(intent_type, "process_task")
        
        # Basic customization based on entities
        if "files" in entities and intent_type == "analysis":
            return "analyze_files"
        elif "languages" in entities and intent_type == "code_generation":
            return "generate_code"
        
        return base_function
    
    def _suggest_best_agent_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Suggest the best core agent for a given task or intent.
        Basic agent suggestion for open source users.
        """
        intent_type = input_data.get("intent_type", "general")
        entities = input_data.get("entities", {})
        
        # Score core agents based on capabilities
        agent_scores: Dict[str, int] = {}
        
        for agent, capabilities in self.core_agent_capabilities.items():
            score = 0
            
            # Intent matching
            if intent_type in capabilities:
                score += 10
            
            # Entity matching
            for entity_type, entity_values in entities.items():
                if entity_type in capabilities or any(
                    val.lower() in capabilities for val in entity_values if isinstance(val, str)
                ):
                    score += 5
            
            if score > 0:
                agent_scores[agent] = score
        
        # Sort by score
        sorted_agents = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)
        
        suggestions = [
            {
                "agent_id": agent,
                "score": score,
                "capabilities": self.core_agent_capabilities[agent],
                "confidence": min(score / 15.0, 1.0)  # Normalize to 0-1
            }
            for agent, score in sorted_agents[:2]  # Top 2 suggestions for core
        ]
        
        return {
            "success": True,
            "suggestions": suggestions,
            "best_match": suggestions[0] if suggestions else None,
            "core_mode": True,
            "note": "Limited to core agents - upgrade for full agent ecosystem"
        }
    
    def _validate_task_structure_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Basic task structure validation for core functionality.
        """
        task = input_data.get("task", {})
        
        if not task:
            return {"success": False, "error": "Task structure is required"}
        
        # Core required fields
        core_required_fields = ["id", "priority", "agent_id", "function", "created_at"]
        missing_fields = [field for field in core_required_fields if field not in task]
        
        if missing_fields:
            return {
                "success": False,
                "error": f"Missing required fields: {missing_fields}",
                "validation_score": 0.0,
                "core_mode": True
            }
        
        # Basic validation checks
        validation_issues: list[str] = []
        score = 1.0
        
        # Priority validation
        if not isinstance(task.get("priority"), int) or not 1 <= task["priority"] <= 10:
            validation_issues.append("Priority must be an integer between 1 and 10")
            score -= 0.3
        
        # Agent ID validation (core agents only)
        if task["agent_id"] not in self.core_agent_capabilities:
            validation_issues.append(f"Unknown core agent_id: {task['agent_id']}")
            score -= 0.4
        
        # Function validation
        if not isinstance(task.get("function"), str) or len(task["function"]) < 3:
            validation_issues.append("Function name should be a meaningful string")
            score -= 0.2
        
        # Timestamp validation
        try:
            datetime.fromisoformat(task["created_at"].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            validation_issues.append("Invalid created_at timestamp format")
            score -= 0.1
        
        score = max(score, 0.0)  # Ensure non-negative
        
        return {
            "success": True,
            "valid": len(validation_issues) == 0,
            "validation_score": score,
            "issues": validation_issues,
            "task_id": task.get("id", "unknown"),
            "core_mode": True
        }
    
    def parse_prompt_to_task(self, prompt: str) -> Dict[str, Any]:
        """
        Legacy method for backward compatibility.
        Convert a user prompt into a structured OrbitSuite task dict.
        
        This maintains compatibility with existing integrations while
        providing core functionality for open source users.
        """
        try:
            # Quick core analysis for legacy mode
            intent_type = "general"
            for pattern_type, patterns in self.core_intent_patterns.items():
                if any(re.search(pattern, prompt.lower()) for pattern in patterns):
                    intent_type = pattern_type
                    break
            
            # Basic entity extraction
            entities = self._extract_core_entities(prompt)
            
            # Generate core task
            task = {
                "id": f"core_legacy_{uuid.uuid4().hex[:8]}",
                "priority": self._estimate_core_priority(prompt, intent_type),
                "depends_on": [],
                "agent_id": self._suggest_core_agent_for_intent(intent_type, entities) or "engineer",
                "function": self._generate_core_function_name(intent_type, entities),
                "arguments": {
                    "description": prompt,
                    "intent_type": intent_type,
                    "entities": entities,
                    "legacy_mode": True,
                    "core_mode": True
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "core_edition": True,
                    "linguist_version": self.version
                }
            }
            
            log_step(f"TaskLinguistCore legacy parsed: {prompt} -> {intent_type}")
            return task
        
        except Exception as e:
            log_step(f"Core legacy parsing failed: {e}")
            return {
                "id": f"core_invalid_{uuid.uuid4().hex[:8]}",
                "priority": 1,
                "function": "noop",
                "arguments": {
                    "reason": "core_parse_error", 
                    "error": str(e),
                    "core_mode": True
                },
                "depends_on": [],
                "agent_id": "engineer",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {"core_edition": True}
            }
    
    def _clear_core_cache(self) -> Dict[str, Any]:
        """Clear the core intent recognition cache."""
        cache_size = len(self.core_intent_cache)
        self.core_intent_cache.clear()
        
        return {
            "success": True,
            "message": f"Cleared {cache_size} cached core intents",
            "cache_size": 0,
            "core_mode": True
        }
    
    def _get_core_status(self) -> Dict[str, Any]:
        """
        Get core task linguist status and basic statistics.
        Provides essential status information for open source users.
        """
        return {
            "success": True,
            "linguist": "task_linguist_core",
            "version": self.version,
            "edition": "Open Core",
            "description": self.description,
            "statistics": {
                "cache_size": len(self.core_intent_cache)
            },
            "capabilities": {
                "supported_intents": list(self.core_intent_patterns.keys()),
                "supported_agents": list(self.core_agent_capabilities.keys()),
                "complexity_levels": ["low", "medium", "high"]
            },
            "core_features": [
                "Pattern-based intent recognition",
                "Basic entity extraction",
                "Core complexity assessment",
                "Agent capability mapping",
                "Task structure generation",
                "Legacy compatibility"
            ],
            "upgrade_features": [
                "AI-powered task decomposition",
                "Advanced analytics and history",
                "Enterprise agent ecosystem",
                "Complex validation scoring",
                "Advanced caching strategies",
                "Professional support"
            ],
            "configuration": {
                "max_cache_size": 100,  # Limited for core
                "cache_enabled": True,
                "ai_decomposition": False,
                "enterprise_features": False
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Export core agent instance for open source users
agent = TaskLinguistCore()

# Compatibility alias for existing integrations
task_linguist_core = agent
