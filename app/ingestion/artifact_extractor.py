"""
DriftGuard Artifact Extractor
Extracts structured information from source files, documentation, configs,
specs, and manifests to build an accurate repository relationship graph.
"""

import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ExtractedElement:
    """An extracted fact with its location for evidence verification."""
    value: str
    line_num: int
    context: str = ""


@dataclass
class ExtractedInfo:
    """Structured information extracted from an artifact."""
    functions: List[ExtractedElement] = field(default_factory=list)
    classes: List[ExtractedElement] = field(default_factory=list)
    imports: List[ExtractedElement] = field(default_factory=list)
    api_routes: List[ExtractedElement] = field(default_factory=list)
    test_names: List[ExtractedElement] = field(default_factory=list)
    dependencies: List[ExtractedElement] = field(default_factory=list)
    config_keys: List[ExtractedElement] = field(default_factory=list)
    referenced_paths: List[ExtractedElement] = field(default_factory=list)
    commands: List[ExtractedElement] = field(default_factory=list)

    def summary(self) -> Dict[str, int]:
        return {
            "functions": len(self.functions),
            "classes": len(self.classes),
            "imports": len(self.imports),
            "api_routes": len(self.api_routes),
            "test_names": len(self.test_names),
            "dependencies": len(self.dependencies),
            "config_keys": len(self.config_keys),
            "referenced_paths": len(self.referenced_paths),
            "commands": len(self.commands),
        }


def _get_line_num(content: str, match_idx: int) -> int:
    return content.count('\n', 0, match_idx) + 1


def extract_python_info(content: str) -> ExtractedInfo:
    """Extract structured info from Python source code."""
    info = ExtractedInfo()

    # Functions
    for m in re.finditer(r'^\s*(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)', content, re.MULTILINE):
        line_num = _get_line_num(content, m.start())
        info.functions.append(ExtractedElement(value=f"{m.group(1)}({m.group(2).strip()})", line_num=line_num))

    # Classes
    for m in re.finditer(r'^\s*class\s+(\w+)', content, re.MULTILINE):
        line_num = _get_line_num(content, m.start())
        info.classes.append(ExtractedElement(value=m.group(1), line_num=line_num))

    # Imports
    for m in re.finditer(r'^\s*(?:from\s+(\S+)\s+)?import\s+(.+)$', content, re.MULTILINE):
        module = m.group(1) or m.group(2).split(',')[0].strip().split(' as ')[0].strip()
        line_num = _get_line_num(content, m.start())
        info.imports.append(ExtractedElement(value=module, line_num=line_num))

    # API routes (Flask/FastAPI/Django patterns)
    for m in re.finditer(r'@\w+\.(get|post|put|delete|patch|route)\s*\(\s*["\']([^"\']+)', content, re.IGNORECASE):
        line_num = _get_line_num(content, m.start())
        info.api_routes.append(ExtractedElement(value=f"{m.group(1).upper()} {m.group(2)}", line_num=line_num))

    # Test names
    for m in re.finditer(r'^\s*(?:async\s+)?def\s+(test_\w+)', content, re.MULTILINE):
        line_num = _get_line_num(content, m.start())
        info.test_names.append(ExtractedElement(value=m.group(1), line_num=line_num))

    # Env vars
    for m in re.finditer(r'os\.(?:getenv|environ(?:\[|\.get\())\s*["\']([A-Z0-9_]+)["\']', content):
        line_num = _get_line_num(content, m.start())
        info.config_keys.append(ExtractedElement(value=m.group(1), line_num=line_num))

    return info


def extract_js_ts_info(content: str) -> ExtractedInfo:
    """Extract structured info from JavaScript/TypeScript source code."""
    info = ExtractedInfo()

    # Functions
    for m in re.finditer(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)', content):
        line_num = _get_line_num(content, m.start())
        info.functions.append(ExtractedElement(value=f"{m.group(1)}({m.group(2).strip()})", line_num=line_num))
        
    for m in re.finditer(r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*=>', content):
        line_num = _get_line_num(content, m.start())
        info.functions.append(ExtractedElement(value=f"{m.group(1)}({m.group(2).strip()})", line_num=line_num))

    # Classes
    for m in re.finditer(r'class\s+(\w+)', content):
        line_num = _get_line_num(content, m.start())
        info.classes.append(ExtractedElement(value=m.group(1), line_num=line_num))

    # Imports
    for m in re.finditer(r'(?:import|require)\s*\(?\s*["\']([^"\']+)["\']', content):
        line_num = _get_line_num(content, m.start())
        info.imports.append(ExtractedElement(value=m.group(1), line_num=line_num))
    for m in re.finditer(r'from\s+["\']([^"\']+)["\']', content):
        line_num = _get_line_num(content, m.start())
        info.imports.append(ExtractedElement(value=m.group(1), line_num=line_num))

    # Express/Fastify routes
    for m in re.finditer(r'\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)', content, re.IGNORECASE):
        line_num = _get_line_num(content, m.start())
        info.api_routes.append(ExtractedElement(value=f"{m.group(1).upper()} {m.group(2)}", line_num=line_num))

    # Test names
    for m in re.finditer(r'(?:it|test|describe)\s*\(\s*["\']([^"\']+)', content):
        line_num = _get_line_num(content, m.start())
        info.test_names.append(ExtractedElement(value=m.group(1), line_num=line_num))

    # Env vars (process.env.VAR)
    for m in re.finditer(r'process\.env\.([A-Z0-9_]+)', content):
        line_num = _get_line_num(content, m.start())
        info.config_keys.append(ExtractedElement(value=m.group(1), line_num=line_num))

    return info


def extract_go_info(content: str) -> ExtractedInfo:
    """Extract structured info from Go source code."""
    info = ExtractedInfo()

    # Functions
    for m in re.finditer(r'func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(([^)]*)\)', content):
        line_num = _get_line_num(content, m.start())
        info.functions.append(ExtractedElement(value=f"{m.group(1)}({m.group(2).strip()})", line_num=line_num))

    # Structs
    for m in re.finditer(r'type\s+(\w+)\s+struct', content):
        line_num = _get_line_num(content, m.start())
        info.classes.append(ExtractedElement(value=m.group(1), line_num=line_num))

    # Imports
    for m in re.finditer(r'"([^"]+)"', content[:4000]):  # Imports are near top
        val = m.group(1)
        if '/' in val or '.' in val or val in ('fmt', 'os', 'net/http', 'context', 'time'):
            line_num = _get_line_num(content, m.start())
            info.imports.append(ExtractedElement(value=val, line_num=line_num))

    # Test names
    for m in re.finditer(r'func\s+(Test\w+)\s*\(', content):
        line_num = _get_line_num(content, m.start())
        info.test_names.append(ExtractedElement(value=m.group(1), line_num=line_num))

    # HTTP routes
    for m in re.finditer(r'(?:Handle|HandleFunc|GET|POST|PUT|DELETE)\s*\(\s*["\']([^"\']+)', content):
        line_num = _get_line_num(content, m.start())
        info.api_routes.append(ExtractedElement(value=m.group(1), line_num=line_num))

    # Env vars
    for m in re.finditer(r'os\.Getenv\s*\(\s*["\']([A-Z0-9_]+)["\']', content):
        line_num = _get_line_num(content, m.start())
        info.config_keys.append(ExtractedElement(value=m.group(1), line_num=line_num))

    return info


def extract_rust_info(content: str) -> ExtractedInfo:
    """Extract structured info from Rust source code."""
    info = ExtractedInfo()

    for m in re.finditer(r'(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*(?:<[^>]*>)?\s*\(([^)]*)\)', content):
        line_num = _get_line_num(content, m.start())
        info.functions.append(ExtractedElement(value=f"{m.group(1)}({m.group(2).strip()})", line_num=line_num))

    for m in re.finditer(r'(?:pub\s+)?(?:struct|enum)\s+(\w+)', content):
        line_num = _get_line_num(content, m.start())
        info.classes.append(ExtractedElement(value=m.group(1), line_num=line_num))

    for m in re.finditer(r'use\s+([^;]+);', content):
        line_num = _get_line_num(content, m.start())
        info.imports.append(ExtractedElement(value=m.group(1).strip(), line_num=line_num))

    for m in re.finditer(r'#\[test\]\s*(?:async\s+)?fn\s+(\w+)', content, re.DOTALL):
        line_num = _get_line_num(content, m.start())
        info.test_names.append(ExtractedElement(value=m.group(1), line_num=line_num))

    return info


def extract_java_info(content: str) -> ExtractedInfo:
    """Extract structured info from Java source code."""
    info = ExtractedInfo()

    for m in re.finditer(r'(?:public|private|protected)?\s*class\s+(\w+)', content):
        line_num = _get_line_num(content, m.start())
        info.classes.append(ExtractedElement(value=m.group(1), line_num=line_num))

    for m in re.finditer(r'(?:public|private|protected)\s+(?:static\s+)?(?:\w+(?:<[^>]+>)?)\s+(\w+)\s*\(([^)]*)\)', content):
        line_num = _get_line_num(content, m.start())
        info.functions.append(ExtractedElement(value=f"{m.group(1)}({m.group(2).strip()})", line_num=line_num))

    for m in re.finditer(r'import\s+([\w.]+);', content):
        line_num = _get_line_num(content, m.start())
        info.imports.append(ExtractedElement(value=m.group(1), line_num=line_num))

    for m in re.finditer(r'@Test\s+.*?(?:public\s+)?void\s+(\w+)', content, re.DOTALL):
        line_num = _get_line_num(content, m.start())
        info.test_names.append(ExtractedElement(value=m.group(1), line_num=line_num))

    return info


def extract_dependency_info(content: str, filename: str) -> ExtractedInfo:
    """Extract dependency names and versions from manifest files."""
    info = ExtractedInfo()

    if filename.endswith('.json'):
        try:
            data = json.loads(content)
            for key in ['dependencies', 'devDependencies', 'peerDependencies']:
                if key in data and isinstance(data[key], dict):
                    for dep, ver in data[key].items():
                        line_num = content[:content.find(f'"{dep}"')].count('\n') + 1 if f'"{dep}"' in content else 1
                        info.dependencies.append(ExtractedElement(value=f"{dep} {ver}", line_num=line_num))
        except Exception:
            pass

    elif 'requirements' in filename.lower() and filename.endswith('.txt'):
        for i, line in enumerate(content.split('\n')):
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('-'):
                info.dependencies.append(ExtractedElement(value=line, line_num=i+1))

    elif filename == 'go.mod':
        for m in re.finditer(r'^\s*(\S+)\s+(v[0-9A-Za-z.\-+]+)', content, re.MULTILINE):
            line_num = _get_line_num(content, m.start())
            info.dependencies.append(ExtractedElement(value=f"{m.group(1)} {m.group(2)}", line_num=line_num))

    elif filename.lower() == 'cargo.toml':
        in_deps = False
        for i, line in enumerate(content.split('\n')):
            if re.match(r'\[.*dependencies.*\]', line):
                in_deps = True
                continue
            if line.startswith('[') and in_deps:
                in_deps = False
            if in_deps:
                m = re.match(r'(\w[\w-]*)\s*=\s*(.+)', line)
                if m:
                    info.dependencies.append(ExtractedElement(value=f"{m.group(1)} {m.group(2).strip()}", line_num=i+1))

    elif filename.lower() == 'gemfile':
        for m in re.finditer(r"gem\s+['\"]([^'\"]+)['\"](?:\s*,\s*['\"]([^'\"]+)['\"])?", content):
            line_num = _get_line_num(content, m.start())
            val = m.group(1) + (f" {m.group(2)}" if m.group(2) else "")
            info.dependencies.append(ExtractedElement(value=val, line_num=line_num))

    elif filename.lower() == 'pyproject.toml':
        # Supports:
        # - PEP 621: [project] dependencies = ["pkg>=version", ...]
        # - Poetry:  [tool.poetry.dependencies] pkg = "^1.0"
        # - PDM/Hatch dependency-groups: [dependency-groups] tests = ["pytest", ...]
        IGNORED_KEYS = {
            'name', 'version', 'description', 'python', 'readme',
            'license', 'authors', 'homepage', 'repository', 'keywords',
            'classifiers', 'dynamic', 'requires', 'build-backend',
            'requires-python',
        }
        # Sections that carry dependency declarations
        DEP_SECTIONS = {
            'project',
            'tool.poetry.dependencies',
            'tool.poetry.dev-dependencies',
            'tool.poetry.group.dev.dependencies',
        }
        # Key names whose values ARE package lists
        DEP_LIST_KEYS = {
            'dependencies', 'dev', 'tests', 'docs', 'extras',
            'dev-dependencies', 'optional-dependencies', 'github-actions',
        }
        # Key names whose values are lists but NOT package lists
        NON_DEP_LIST_KEYS = {
            'authors', 'classifiers', 'keywords', 'license-files', 'maintainers',
            'source', 'source-includes', 'data', 'packages', 'include', 'exclude',
        }

        current_section = ''
        in_dep_list = False
        bracket_depth = 0

        for i, line in enumerate(content.split('\n')):
            stripped = line.strip()

            # Section header: [project], [dependency-groups], [[tool.poetry.dependencies]] etc.
            header_m = re.match(r'^\[\[?([^\]]+)\]\]?$', stripped)
            if header_m:
                current_section = header_m.group(1).strip().lower()
                in_dep_list = False
                bracket_depth = 0
                continue

            in_known_dep_section = bool(
                current_section in DEP_SECTIONS
                or current_section.startswith('dependency-groups')
                or re.match(r'tool\.poetry\.group\.\w+\.dependencies', current_section)
            )

            # Detect start of a key = [...] assignment
            list_key_m = re.match(r'^(\w[\w-]*)\s*=\s*\[', stripped)
            if list_key_m and in_known_dep_section:
                key_name = list_key_m.group(1).lower()
                # Only enter dep-list mode for keys that actually carry package names
                is_dep_list = (
                    key_name in DEP_LIST_KEYS
                    or (
                        current_section.startswith('dependency-groups')
                        and key_name not in NON_DEP_LIST_KEYS
                    )
                )
                if is_dep_list:
                    in_dep_list = True
                    bracket_depth = stripped.count('[') - stripped.count(']')
                    bracket_pos = stripped.index('[')
                    # Extract any package names on the opening line
                    for pkg_m in re.finditer(r'["\']([A-Za-z][\w._-]*)', stripped[bracket_pos:]):
                        info.dependencies.append(
                            ExtractedElement(value=pkg_m.group(1), line_num=i + 1)
                        )
                    if bracket_depth <= 0:
                        in_dep_list = False
                # else: non-dep list (authors, classifiers, etc.) — skip it entirely
                continue

            if in_dep_list:
                bracket_depth += stripped.count('[') - stripped.count(']')
                if bracket_depth <= 0:
                    in_dep_list = False
                # Skip inline table entries like { include-group = "dev" }
                if not stripped.startswith('{'):
                    for pkg_m in re.finditer(r'["\']([A-Za-z][\w._-]*)', stripped):
                        info.dependencies.append(
                            ExtractedElement(value=pkg_m.group(1), line_num=i + 1)
                        )
                continue

            # Poetry-style inline: fastapi = "^0.95.0"
            if in_known_dep_section:
                key_m = re.match(r'^([A-Za-z][\w-]*)\s*=\s*["\'{]', stripped)
                if key_m and key_m.group(1).lower() not in IGNORED_KEYS:
                    info.dependencies.append(
                        ExtractedElement(value=key_m.group(1), line_num=i + 1)
                    )

    return info


def extract_docker_info(content: str) -> ExtractedInfo:
    """Extract structured facts from Dockerfiles."""
    info = ExtractedInfo()
    for i, line in enumerate(content.split('\n')):
        line_clean = line.strip()
        if not line_clean or line_clean.startswith('#'):
            continue
        line_num = i + 1
        if line_clean.upper().startswith('FROM '):
            info.dependencies.append(ExtractedElement(value=f"base_image:{line_clean[5:].strip()}", line_num=line_num))
        elif line_clean.upper().startswith('EXPOSE '):
            info.config_keys.append(ExtractedElement(value=f"port:{line_clean[7:].strip()}", line_num=line_num))
        elif line_clean.upper().startswith('ENV '):
            info.config_keys.append(ExtractedElement(value=f"env:{line_clean[4:].strip()}", line_num=line_num))
        elif line_clean.upper().startswith('COPY ') or line_clean.upper().startswith('ADD '):
            parts = line_clean.split()
            if len(parts) >= 3:
                info.referenced_paths.append(ExtractedElement(value=parts[1], line_num=line_num))
        elif line_clean.upper().startswith('ENTRYPOINT ') or line_clean.upper().startswith('CMD '):
            info.commands.append(ExtractedElement(value=line_clean, line_num=line_num))
    return info


def extract_doc_info(content: str) -> ExtractedInfo:
    """Extract documented endpoints, env vars, paths, and commands from documentation."""
    info = ExtractedInfo()

    for i, line in enumerate(content.split('\n')):
        line_num = i + 1
        line_clean = line.strip()

        # Documented HTTP API Endpoints (e.g. `POST /api/v1/clusters`, `GET /users`)
        for m in re.finditer(r'\b(GET|POST|PUT|DELETE|PATCH)\s+([/\w\-{}]+)', line_clean):
            info.api_routes.append(ExtractedElement(value=f"{m.group(1)} {m.group(2)}", line_num=line_num))

        # Documented Environment Variables (e.g. `REDIS_PASSWORD`, `API_PORT`)
        for m in re.finditer(r'\b([A-Z][A-Z0-9_]{3,})\b', line_clean):
            word = m.group(1)
            # Filter common words
            if word not in {'HTTP', 'HTTPS', 'JSON', 'YAML', 'HTML', 'REST', 'TRUE', 'FALSE', 'NULL', 'NONE'}:
                info.config_keys.append(ExtractedElement(value=word, line_num=line_num))

        # Documented File Paths (e.g. `src/api.py`, `internal/k8sutils/...`, `Dockerfile`, `go.mod`)
        for m in re.finditer(r'(?:`|\b)([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]{1,4})(?:`|\b)', line_clean):
            path_cand = m.group(1)
            if '/' in path_cand or path_cand in ('Dockerfile', 'go.mod', 'package.json', 'Makefile', 'requirements.txt'):
                info.referenced_paths.append(ExtractedElement(value=path_cand, line_num=line_num))

        # Documented CLI / Run Commands (e.g. `helm install`, `make test`, `kubectl apply`)
        if line_clean.startswith(('$', '#', '>')) or '`' in line_clean:
            for m in re.finditer(r'(?:helm|kubectl|docker|docker-compose|make|go|npm|python|pytest)\s+[^\n`$#]+', line_clean):
                info.commands.append(ExtractedElement(value=m.group(0).strip(), line_num=line_num))

    return info


def extract_api_spec_info(content: str) -> ExtractedInfo:
    """Extract OpenAPI/Swagger routes and schemas."""
    info = ExtractedInfo()
    # Find OpenAPI paths: "/some/path":
    for m in re.finditer(r'["\'](/[\w\-/{}.]+)["\']\s*:', content):
        line_num = _get_line_num(content, m.start())
        info.api_routes.append(ExtractedElement(value=m.group(1), line_num=line_num))
    # Find methods: get:, post:, etc.
    for m in re.finditer(r'^\s*(get|post|put|delete|patch):\s*$', content, re.MULTILINE | re.IGNORECASE):
        line_num = _get_line_num(content, m.start())
        info.api_routes.append(ExtractedElement(value=m.group(1).upper(), line_num=line_num))
    return info


def extract_info(content: str, filepath: str) -> ExtractedInfo:
    """
    Extract structured facts from any file based on extension and filename.
    """
    ext = Path(filepath).suffix.lower()
    filename = Path(filepath).name.lower()

    if ext == '.py':
        return extract_python_info(content)
    elif ext in ('.js', '.ts', '.jsx', '.tsx'):
        return extract_js_ts_info(content)
    elif ext == '.go':
        return extract_go_info(content)
    elif ext == '.rs':
        return extract_rust_info(content)
    elif ext == '.java':
        return extract_java_info(content)
    elif filename in ('package.json', 'go.mod', 'cargo.toml', 'gemfile', 'pyproject.toml', 'pipfile', 'setup.cfg', 'setup.py') or 'requirements' in filename:
        return extract_dependency_info(content, filename)
    elif 'dockerfile' in filename:
        return extract_docker_info(content)
    elif ext in ('.md', '.rst', '.txt') or 'doc' in filepath.lower():
        return extract_doc_info(content)
    elif 'openapi' in filename or 'swagger' in filename or ext in ('.graphql', '.gql', '.proto'):
        return extract_api_spec_info(content)
    else:
        return ExtractedInfo()
