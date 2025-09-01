# agents/engineer_core.py
# Clean, minimal EngineerCore implementation for fast artifacts

import json
import re
from dataclasses import dataclass, asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, TypedDict, cast

from .base_agent import BaseAgent

# Simple string constants
NODEJS = "Node.js"
PY_FASTAPI = "Python FastAPI"
EXPRESS = "Express.js"
FASTAPI = "FastAPI"
SPRING_BOOT = "Spring Boot"


@dataclass
class CoreRequirement:
    requirement_id: str
    title: str
    description: str
    type: str
    priority: str


@dataclass
class CoreArchitecturalComponent:
    component_id: str
    name: str
    description: str
    type: str
    technologies: List[str]


class FilePlanEntry(TypedDict, total=False):
    path: str
    purpose: str
    language: str


PLAN_JSON = "plan.json"
SPEC_JSON = "spec.json"
DESIGN_JSON = "design.json"
SUMMARY_JSON = "summary.json"
SUMMARY_MD = "summary.md"


class EngineerCore(BaseAgent):
    def __init__(self, output_dir: str | None = None) -> None:
        super().__init__(name="engineer_core")
        self.description = "Open-source system architecture and design planning"
        self.version = "1.0.1"
        self.license_tier = "open_core"
        # When running frozen (PyInstaller), Path.cwd() points to the dist directory.
        # We want artifacts to land beside the executable in ./output rather than nested inside dist.
        if output_dir:
            # Use provided task-specific directory
            self.engineering_root = Path(output_dir) / 'engineering'
        else:
            # Fall back to default behavior for backward compatibility
            cwd = Path.cwd()
            if getattr(__import__('sys'), 'frozen', False):  # type: ignore[attr-defined]
                # For a frozen build, place artifacts one directory above if that directory exists
                parent = cwd.parent if (cwd.name.lower() == 'dist' and cwd.parent.exists()) else cwd
                self.engineering_root = parent / 'output' / 'engineering'
            else:
                self.engineering_root = cwd / 'output' / 'engineering'

        self.core_design_patterns: Dict[str, Dict[str, Any]] = {
            "microservices": {
                "description": "Distributed architecture with independent services",
                "benefits": ["scalability", "maintainability", "technology_diversity"],
                "use_cases": ["large_teams", "complex_domains", "independent_deployment"],
            },
            "monolithic": {
                "description": "Single deployable unit architecture",
                "benefits": ["simplicity", "easier_testing", "single_deployment"],
                "use_cases": ["small_teams", "simple_domains", "rapid_prototyping"],
            },
            "layered": {
                "description": "Hierarchical organization of components",
                "benefits": ["separation_of_concerns", "reusability", "testability"],
                "use_cases": ["traditional_applications", "clear_boundaries", "team_structure"],
            },
        }

        self.core_technology_stacks: Dict[str, Dict[str, Any]] = {
            "web_application": {
                "frontend": ["React", "Vue.js", "Angular"],
                "backend": [NODEJS, PY_FASTAPI, "Java Spring"],
                "database": ["PostgreSQL", "MongoDB", "SQLite"],
                "deployment": ["Docker", "Basic Cloud"],
            },
            "api_service": {
                "frameworks": [FASTAPI, EXPRESS, SPRING_BOOT],
                "authentication": ["JWT", "Basic Auth"],
                "documentation": ["OpenAPI", "Swagger"],
                "testing": ["Postman", "Jest", "Pytest"],
            },
            "data_processing": {
                "languages": ["Python", "JavaScript", "Java"],
                "frameworks": ["Pandas", f"{NODEJS} Streams", "Spring Batch"],
                "storage": ["CSV", "JSON", "Database"],
                "scheduling": ["Cron", "Basic Schedulers"],
            },
        }

        self.core_analysis_patterns: Dict[str, str] = {
            "scalability": r"(scale|load|performance|users)",
            "security": r"(security|auth|secure)",
            "reliability": r"(reliable|backup|uptime)",
            "maintainability": r"(maintain|update|modify)",
            "integration": r"(integrate|api|connect)",
        }

        self.core_planning_templates: Dict[str, List[str]] = {
            "web_app": [
                "requirements_analysis",
                "basic_design",
                "technology_selection",
                "development_planning",
                "testing_approach",
            ],
            "api_service": [
                "requirements_analysis",
                "api_design",
                "authentication_planning",
                "testing_strategy",
                "deployment_basics",
            ],
            "data_processing": [
                "data_analysis",
                "processing_design",
                "storage_planning",
                "scheduling_approach",
                "monitoring_basics",
            ],
        }

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Accept legacy string usage and normalize
        if not isinstance(input_data, dict):  # type: ignore[truthy-bool]
            input_data = {"command": "analyze", "description": str(input_data)}  # type: ignore[assignment]
        
        # Check for dynamic output directory override
        original_engineering_root = self.engineering_root
        output_dir = input_data.get("output_dir")
        if output_dir:
            self.engineering_root = Path(output_dir) / 'engineering'
        
        try:
            command = input_data.get("command", "analyze")
            if command == "analyze":
                return self._analyze_system_core(input_data)
            if command == "plan_files":
                return self._plan_files_core(input_data)
            if command == "requirements":
                return self._analyze_requirements_core(input_data)
            if command == "recommend_stack":
                return self._recommend_core_technology_stack(input_data)
            if command == "get_patterns":
                return self._get_core_design_patterns(input_data)
            if command == "plan_steps":
                return self._generate_core_planning_steps(input_data)
            if command == "status":
                return self._get_core_status()
            return {
                "success": False,
                "error": f"Unknown core engineering command: {command}",
            }
        finally:
            # Always restore original engineering root
            self.engineering_root = original_engineering_root

    def _analyze_system_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Core system analysis with optional NL mode LLM augmentation."""
        raw_spec = input_data.get("spec", {})
        spec: Dict[str, Any] = cast(Dict[str, Any], raw_spec) if isinstance(raw_spec, dict) else {}
        project_type = input_data.get("project_type", "general")
        nl_mode = bool(str(__import__('os').getenv('ORBITSUITE_NL_MODE', '0')) in ('1','true','True'))
        # Optional: augment spec using LLM when enabled
        if nl_mode and not spec.get('requirements'):
            try:
                from .llm_provider import get_provider_from_env  # type: ignore
                provider = get_provider_from_env()
                prompt_desc = input_data.get('description') or spec.get('description','')
                if prompt_desc:
                    messages = [
                        {"role": "system", "content": "You extract structured software requirements."},
                        {"role": "user", "content": f"Analyze this request and list functional requirements, non-functional requirements, and a short component breakdown as JSON with keys requirements, non_functional, components.\nRequest: {prompt_desc}"}
                    ]
                    llm_out = provider.generate(messages)
                    if llm_out and llm_out.strip().startswith('{'):
                        import json as _json
                        try:
                            parsed = _json.loads(llm_out)
                            if isinstance(parsed, dict):
                                spec.setdefault('requirements', parsed.get('requirements', []))  # type: ignore[arg-type]
                                spec.setdefault('non_functional', parsed.get('non_functional', []))  # type: ignore[arg-type]
                                spec.setdefault('components', parsed.get('components', []))  # type: ignore[arg-type]
                        except Exception:
                            pass
            except Exception:
                pass

        synthesized = False
        if not spec:
            # Try fallbacks commonly used by upstream callers
            fallback_desc = (
                input_data.get("description")
                or input_data.get("prompt")
                or input_data.get("goal")
            )
            if fallback_desc:
                spec = {"description": str(fallback_desc)}
            else:
                # As a last resort, synthesize a generic description from available fields
                pname = input_data.get("project_name") or project_type or "core"
                spec = {
                    "description": (
                        f"Initial lightweight analysis for '{pname}' ({project_type}). "
                        "No explicit spec provided; using default concerns for reliability and maintainability."
                    ),
                    "requirements": [],
                }
            synthesized = True

        requirements = self._extract_core_requirements(spec)
        concerns = self._analyze_core_concerns(spec)
        architecture_recommendation = self._recommend_core_architecture(project_type, concerns)

        analysis_result: Dict[str, Any] = {
            "analysis_id": f"core_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "project_type": project_type,
            "requirements_count": len(requirements),
            "system_concerns": concerns,
            "architecture_recommendation": architecture_recommendation,
            "next_steps": self.core_planning_templates.get(
                project_type, ["requirements_analysis", "basic_design"]
            ),
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "license_tier": self.license_tier,
            # Traceability and gentle notice when we had to infer inputs
            "input_trace": {
                "project_name": input_data.get("project_name"),
                "received_keys": sorted(input_data),
            },
            **({"warning": "No spec provided; performed best-effort core analysis from defaults"} if synthesized else {}),
        }

        out_dir = self._ensure_engineering_dir(input_data.get("project_name") or project_type)
        # Prepare a minimal system spec artifact (engineer provides the spec when missing)
        spec_artifact: Dict[str, Any] = {
            "project_name": input_data.get("project_name"),
            "project_type": project_type,
            "source": "synthesized" if synthesized else "provided",
            "spec": {
                "description": spec.get("description", ""),
                "requirements": self._to_jsonable(requirements),
            },
            "derived_concerns": concerns,
        }

        # Prepare a lightweight planning artifact so consumers get a complete set in one pass
        plan_steps = self.core_planning_templates.get(
            project_type,
            [
                "requirements_analysis",
                "basic_design",
                "technology_selection",
                "development_planning",
                "testing_approach",
            ],
        )
        plan_artifact: Dict[str, Any] = {
            "project_name": input_data.get("project_name"),
            "project_type": project_type,
            "steps": plan_steps,
            "step_descriptions": {
                "requirements_analysis": "Gather and document functional and non-functional requirements",
                "basic_design": "Create high-level system design and component structure",
                "technology_selection": "Choose appropriate technologies based on requirements",
                "development_planning": "Plan development phases and milestones",
                "testing_approach": "Define testing strategy and quality assurance",
            },
        }

        # Design artifact (lightweight) capturing architecture recommendation & components
        design_artifact: Dict[str, Any] = {
            "project_name": input_data.get("project_name"),
            "project_type": project_type,
            "architecture": architecture_recommendation,
            "created": datetime.now(timezone.utc).isoformat(),
        }

        files_payload: Dict[str, Any] = {
            SUMMARY_JSON: analysis_result,
            SUMMARY_MD: self._render_summary_md(analysis_result),
            SPEC_JSON: spec_artifact,
            PLAN_JSON: plan_artifact,
            DESIGN_JSON: design_artifact,
        }
        files_written = self._write_artifacts(out_dir, files_payload)
        # Provide direct lookup paths for orchestrator artifact propagation
        spec_path = str(out_dir / SPEC_JSON)
        plan_path = str(out_dir / PLAN_JSON)
        design_path = str(out_dir / DESIGN_JSON)
        return {
            "success": True,
            "core_analysis": analysis_result,
            "artifact_dir": str(out_dir),
            "files_written": files_written,
            "spec_path": spec_path,
            "plan_path": plan_path,
            "design_path": design_path,
        }

    def _extract_core_requirements(self, spec: Dict[str, Any]) -> List[CoreRequirement]:
        requirements: List[CoreRequirement] = []
        description = spec.get("description", "")
        if description:
            non_functional_keywords = ["performance", "security", "usability", "reliability"]
            sentences = description.split(".")
            for i, sentence in enumerate(sentences):
                s = sentence.strip()
                if not s:
                    continue
                req_type = "non_functional" if any(kw in s.lower() for kw in non_functional_keywords) else "functional"
                if any(kw in s.lower() for kw in ["critical", "must", "essential"]):
                    priority = "high"
                elif any(kw in s.lower() for kw in ["nice to have", "optional", "could"]):
                    priority = "low"
                else:
                    priority = "medium"
                requirements.append(
                    CoreRequirement(
                        requirement_id=f"core_req_{i+1}",
                        title=f"Requirement {i+1}",
                        description=s,
                        type=req_type,
                        priority=priority,
                    )
                )

        req_list = spec.get("requirements")
        if isinstance(req_list, list):
            req_list_str: List[str] = []
            for _item in req_list:
                _item = cast(Any, _item)
                if isinstance(_item, str):
                    req_list_str.append(_item)
            for i, req in enumerate(req_list_str):
                requirements.append(
                    CoreRequirement(
                        requirement_id=f"explicit_req_{i+1}",
                        title=f"Explicit Requirement {i+1}",
                        description=req,
                        type="functional",
                        priority="medium",
                    )
                )
        return requirements

    def _analyze_core_concerns(self, spec: Dict[str, Any]) -> Dict[str, List[str]]:
        concerns: Dict[str, List[str]] = {
            "scalability": [],
            "security": [],
            "reliability": [],
            "maintainability": [],
            "integration": [],
        }
        text_content = ""
        for value in spec.values():
            if isinstance(value, str):
                text_content += f" {value}"
            elif isinstance(value, list):
                for item in value:
                    item = cast(Any, item)
                    if isinstance(item, str):
                        text_content += f" {item}"
                    else:
                        text_content += f" {str(item)}"
        text_content = text_content.lower()
        for concern, pattern in self.core_analysis_patterns.items():
            matches = re.findall(pattern, text_content)
            if matches:
                concerns[concern] = list(set(matches))
        return concerns

    def _recommend_core_architecture(self, project_type: str, concerns: Dict[str, List[str]]) -> Dict[str, Any]:
        if any(concerns.get("scalability", [])) and project_type in ["web_application", "api_service"]:
            recommended_pattern = "microservices"
        elif project_type == "data_processing":
            recommended_pattern = "layered"
        else:
            recommended_pattern = "monolithic"
        return {
            "recommended_pattern": recommended_pattern,
            "pattern_info": self.core_design_patterns.get(recommended_pattern, {}),
            "reasoning": f"Based on project type '{project_type}' and identified concerns",
            "basic_components": self._suggest_core_components(project_type),
        }

    def _suggest_core_components(self, project_type: str) -> List[CoreArchitecturalComponent]:
        components: List[CoreArchitecturalComponent] = []
        if project_type == "web_application":
            components = [
                CoreArchitecturalComponent(
                    component_id="comp_1",
                    name="Frontend Application",
                    description="User interface and client-side logic",
                    type="ui",
                    technologies=["React", "Vue.js", "Angular"],
                ),
                CoreArchitecturalComponent(
                    component_id="comp_2",
                    name="Backend API",
                    description="Server-side logic and API endpoints",
                    type="api",
                    technologies=[NODEJS, PY_FASTAPI, "Java Spring"],
                ),
                CoreArchitecturalComponent(
                    component_id="comp_3",
                    name="Database",
                    description="Data storage and persistence",
                    type="database",
                    technologies=["PostgreSQL", "MongoDB", "SQLite"],
                ),
            ]
        elif project_type == "api_service":
            components = [
                CoreArchitecturalComponent(
                    component_id="comp_1",
                    name="API Server",
                    description="RESTful API service",
                    type="service",
                    technologies=[FASTAPI, EXPRESS, SPRING_BOOT],
                ),
                CoreArchitecturalComponent(
                    component_id="comp_2",
                    name="Authentication Module",
                    description="User authentication and authorization",
                    type="service",
                    technologies=["JWT", "OAuth2", "Basic Auth"],
                ),
            ]
        elif project_type == "data_processing":
            components = [
                CoreArchitecturalComponent(
                    component_id="comp_1",
                    name="Data Ingestion",
                    description="Data input and validation",
                    type="service",
                    technologies=["Python Pandas", f"{NODEJS} Streams"],
                ),
                CoreArchitecturalComponent(
                    component_id="comp_2",
                    name="Processing Engine",
                    description="Data transformation and analysis",
                    type="service",
                    technologies=["Python", "JavaScript", "Java"],
                ),
                CoreArchitecturalComponent(
                    component_id="comp_3",
                    name="Output Storage",
                    description="Processed data storage",
                    type="database",
                    technologies=["Database", "File System", "Cloud Storage"],
                ),
            ]
        return components

    def _plan_files_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a simple file plan (optionally via LLM) for downstream multi-file codegen."""
        description = input_data.get('description', '')
        analysis = input_data.get('analysis', {})
        project_type = input_data.get('project_type', 'general')
        nl_mode = bool(str(__import__('os').getenv('ORBITSUITE_NL_MODE', '0')) in ('1','true','True'))
        base_plan: List[FilePlanEntry] = []
        # Heuristic baseline
        desc_l = description.lower()
        # New: simple static landing page / web UI detection
        if any(k in desc_l for k in (
            'landing page', 'homepage', 'home page', 'hero section', 'html', 'css', 'web page', 'website', 'frontend', 'front-end', 'ui layout', 'static site'
        )):
            base_plan = [
                {'path': 'index.html', 'purpose': 'Landing page markup with hero section linking CSS/JS', 'language': 'html'},
                {'path': 'styles.css', 'purpose': 'Styling including gradient background and responsive layout', 'language': 'css'},
                {'path': 'script.js', 'purpose': 'Client-side interactivity & DOM enhancements', 'language': 'javascript'},
                {'path': 'server.py', 'purpose': 'Optional lightweight development server / future backend stub', 'language': 'python'},
            ]
        elif 'calculator' in desc_l:
            base_plan = [
                {'path': 'app/__init__.py', 'purpose': 'package init', 'language': 'python'},
                {'path': 'app/eval.py', 'purpose': 'expression evaluation functions', 'language': 'python'},
                {'path': 'app/gui.py', 'purpose': 'tkinter GUI (if needed)', 'language': 'python'},
                {'path': 'app/cli.py', 'purpose': 'CLI argument parsing & entry', 'language': 'python'},
                {'path': 'main.py', 'purpose': 'entry point orchestrating CLI/GUI', 'language': 'python'},
            ]
        else:
            base_plan = [
                {'path': 'main.py', 'purpose': 'primary entry point', 'language': 'python'},
                {'path': 'app/core.py', 'purpose': 'core logic', 'language': 'python'},
                {'path': 'app/utils.py', 'purpose': 'helpers', 'language': 'python'},
            ]
        if nl_mode:
            try:
                from .llm_provider import get_provider_from_env  # type: ignore
                provider = get_provider_from_env()
                messages = [
                    {"role": "system", "content": "You design a concise file/module plan for a Python project. Output JSON list with objects {path,purpose,language}."},
                    {"role": "user", "content": f"Project type: {project_type}. Description: {description}. Existing analysis summary keys: {list(analysis)[:6]}"}
                ]
                llm_out = provider.generate(messages)
                if llm_out.strip().startswith('['):
                    import json as _json
                    ll_any = _json.loads(llm_out)
                    if isinstance(ll_any, list) and ll_any:
                        filtered: List[FilePlanEntry] = []
                        for entry in ll_any:
                            entry = cast(Dict[str, Any], entry)
                            if isinstance(entry.get('path'), str):
                                path_val = cast(Any, entry.get('path'))
                                purpose_val = entry.get('purpose', '')
                                lang_val = entry.get('language', 'python')
                                fp: FilePlanEntry = {
                                    'path': str(path_val),
                                    'purpose': str(purpose_val),
                                    'language': str(lang_val),
                                }
                                filtered.append(fp)
                        if filtered:
                            base_plan = filtered
            except Exception:
                pass
        # Write plan artifact
        out_dir = self._ensure_engineering_dir('plan')
        import json as _json
        plan_path = out_dir / 'file_plan.json'
        try:
            plan_path.write_text(_json.dumps(base_plan, indent=2), encoding='utf-8')
        except Exception:
            pass
        return {'success': True, 'plan': base_plan, 'plan_dir': str(out_dir)}

    def _analyze_requirements_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        requirements_text = input_data.get("requirements", "")
        if not requirements_text:
            return {"success": False, "error": "Requirements text is required"}
        lines = [line.strip() for line in requirements_text.split("\n") if line.strip()]
        requirements: List[Dict[str, Any]] = []
        for i, line in enumerate(lines):
            req_type = (
                "non_functional"
                if any(kw in line.lower() for kw in ["performance", "security", "usability", "reliability"])
                else "functional"
            )
            if any(kw in line.lower() for kw in ["critical", "must", "essential"]):
                priority = "high"
            elif any(kw in line.lower() for kw in ["nice", "optional", "could"]):
                priority = "low"
            else:
                priority = "medium"
            requirements.append({"id": f"req_{i+1}", "text": line, "type": req_type, "priority": priority})
        categorized: Dict[str, List[Dict[str, Any]]] = {}
        for req in requirements:
            categorized.setdefault(req["type"], []).append(req)
        return {
            "success": True,
            "core_requirements_analysis": {
                "total_requirements": len(requirements),
                "categories": categorized,
                "basic_recommendations": [
                    "Prioritize high-priority requirements first",
                    "Consider non-functional requirements early in design",
                    "Break down complex requirements into smaller tasks",
                ],
            },
        }

    def _recommend_core_technology_stack(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        project_type = input_data.get("project_type", "web_application")
        constraints_val = input_data.get("constraints", [])
        if isinstance(constraints_val, list):
            constraints: List[str] = []
            for c in constraints_val:
                c = cast(Any, c)
                constraints.append(str(c))
        else:
            constraints = [str(constraints_val)]
        base_stack = self.core_technology_stacks.get(project_type, {})
        if not base_stack:
            return {
                "success": False,
                "error": f"Project type '{project_type}' not supported in core version",
                "supported_types": list(self.core_technology_stacks.keys()),
            }
        customized_stack: Dict[str, Any] = dict(base_stack)
        constraint_text = " ".join(str(c) for c in constraints).lower()
        if "python" in constraint_text and project_type == "web_application":
            customized_stack["backend"] = [PY_FASTAPI, "Django", "Flask"]
        elif "javascript" in constraint_text and project_type == "web_application":
            customized_stack["backend"] = [NODEJS, EXPRESS, "Nest.js"]
        out_dir = self._ensure_engineering_dir(input_data.get("project_name") or project_type)
        payload: Dict[str, Any] = {
            "success": True,
            "core_technology_recommendation": {
                "project_type": project_type,
                "technology_stack": customized_stack,
                "basic_reasoning": f"Recommended stack for {project_type} with basic constraint handling",
                "next_steps": [
                    "Evaluate team expertise with recommended technologies",
                    "Consider scalability requirements",
                    "Plan for deployment and hosting",
                ],
            },
        }
        files_written = self._write_artifacts(out_dir, {"stack.json": payload["core_technology_recommendation"]})
        payload["artifact_dir"] = str(out_dir)
        payload["files_written"] = files_written
        return payload

    def _get_core_design_patterns(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        pattern_name = input_data.get("pattern")
        if pattern_name and pattern_name.lower() in self.core_design_patterns:
            pattern_info = self.core_design_patterns[pattern_name.lower()]
            return {"success": True, "core_pattern": {pattern_name: pattern_info}}
        elif pattern_name:
            return {
                "success": False,
                "error": f"Pattern '{pattern_name}' not available in core version",
                "available_patterns": list(self.core_design_patterns.keys()),
            }
        return {"success": True, "core_patterns": self.core_design_patterns}

    def _generate_core_planning_steps(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        project_type = input_data.get("project_type", "web_application")
        steps = self.core_planning_templates.get(
            project_type,
            [
                "requirements_analysis",
                "basic_design",
                "technology_selection",
                "development_planning",
                "testing_approach",
            ],
        )
        out_dir = self._ensure_engineering_dir(input_data.get("project_name") or project_type)
        payload: Dict[str, Any] = {
            "success": True,
            "core_planning_steps": {
                "project_type": project_type,
                "steps": steps,
                "step_descriptions": {
                    "requirements_analysis": "Gather and document functional and non-functional requirements",
                    "basic_design": "Create high-level system design and component structure",
                    "technology_selection": "Choose appropriate technologies based on requirements",
                    "development_planning": "Plan development phases and milestones",
                    "testing_approach": "Define testing strategy and quality assurance",
                },
            },
        }
        files_written = self._write_artifacts(out_dir, {"plan.json": payload["core_planning_steps"]})
        payload["artifact_dir"] = str(out_dir)
        payload["files_written"] = files_written
        return payload

    def _get_core_status(self) -> Dict[str, Any]:
        return {
            "success": True,
            "agent": self.name,
            "version": self.version,
            "license_tier": self.license_tier,
            "core_capabilities": [
                "basic_system_analysis",
                "requirements_parsing",
                "core_technology_recommendations",
                "basic_architecture_patterns",
                "planning_step_generation",
            ],
            "available_patterns": list(self.core_design_patterns.keys()),
            "supported_project_types": list(self.core_technology_stacks.keys()),
            "last_analysis": datetime.now(timezone.utc).isoformat(),
        }

    def _ensure_engineering_dir(self, base_name: str) -> Path:
        slug = re.sub(r"[^a-z0-9]+", "-", (base_name or "core").lower()).strip("-") or "core"
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out = self.engineering_root / f"{slug}_{ts}"
        out.mkdir(parents=True, exist_ok=True)
        return out

    def _write_artifacts(self, out_dir: Path, files: Dict[str, Any]) -> List[str]:
        written: List[str] = []
        for name, content in files.items():
            p = out_dir / name
            try:
                serializable = self._to_jsonable(content)
                if isinstance(serializable, (dict, list)):
                    p.write_text(
                        json.dumps(serializable, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )
                else:
                    p.write_text(str(serializable), encoding="utf-8")
                written.append(str(p))
            except Exception as e:  # pragma: no cover - best effort
                print(f"[EngineerCore] artifact write failed for {p}: {e}")
        return written

    def _render_summary_md(self, summary: Dict[str, Any]) -> str:
        lines: List[str] = []
        lines.append(f"# Core Analysis Summary — {summary.get('project_type','unknown')}")
        lines.append("")
        lines.append(f"Analysis ID: {summary.get('analysis_id')}")
        lines.append(f"Timestamp: {summary.get('analysis_timestamp')}")
        lines.append("")
        lines.append("## Architecture Recommendation")
        rec = summary.get("architecture_recommendation", {})
        lines.append(f"Pattern: {rec.get('recommended_pattern','n/a')}")
        lines.append("")
        lines.append("## Next Steps")
        for step in summary.get("next_steps", []):
            lines.append(f"- {step}")
        lines.append("")
        return "\n".join(lines)

    def _to_jsonable(self, obj: Any) -> Any:
        """Recursively convert dataclasses / iterables while preserving primitive types."""
        if is_dataclass(obj) and not isinstance(obj, type):
            out_dict: Dict[str, Any] = {}
            for k, v in asdict(obj).items():
                out_dict[str(cast(Any, k))] = self._to_jsonable(v)
            return out_dict
        if isinstance(obj, dict):
            norm: Dict[str, Any] = {}
            for k, v in obj.items():
                k = cast(Any, k)
                v = cast(Any, v)
                norm[str(k)] = self._to_jsonable(v)
            return norm
        if isinstance(obj, (list, tuple, set)):
            out_list: List[Any] = []
            for v in obj:
                v = cast(Any, v)
                out_list.append(self._to_jsonable(v))
            return out_list
        # Attempt JSON serialization; fallback to repr
        try:
            json.dumps(obj)
            return obj
        except Exception:
            return repr(obj)


agent = EngineerCore()

