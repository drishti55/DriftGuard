"""
DriftGuard File Classifier
Rule-based file type classification into artifact categories.
Includes explicit filters for vendor, generated, cache, and binary content.
"""

import os
import re
from pathlib import Path
from typing import Optional, Tuple, List, Dict

# Directories that are generated, vendored, or cache artifacts
IGNORED_DIR_NAMES = {
    '.git', 'node_modules', 'vendor', 'themes', '__pycache__', 
    '.pytest_cache', '.mypy_cache', 'dist', 'build', 'target', 
    'out', 'coverage', '.cache', '.venv', 'venv', 'env', 
    '.idea', '.vscode', 'tmp', 'temp', 'bower_components',
    '.tox', '.eggs', '*.egg-info'
}

# Binary & media file extensions that should be explicitly ignored from textual drift analysis
IGNORED_BINARY_EXTENSIONS = {
    # Images & Vector graphics
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp', '.bmp', '.tiff', '.psd',
    # Audio & Video
    '.mp3', '.mp4', '.mov', '.avi', '.flv', '.wav', '.webm',
    # Archives & Compressed files
    '.zip', '.tar', '.gz', '.bz2', '.xz', '.tgz', '.7z', '.rar',
    # Compiled Binaries & Libraries
    '.exe', '.dmg', '.bin', '.so', '.dylib', '.dll', '.class', '.pyc', '.pyo', '.o', '.a', '.wasm',
    # Fonts
    '.ttf', '.woff', '.woff2', '.eot', '.otf',
    # Documents / Heavy Formats
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    # Certificates / Keys
    '.crt', '.pem', '.key', '.pub', '.pfx', '.cer'
}

# Minified files and sourcemaps
IGNORED_MINIFIED_PATTERNS = {
    '.min.js', '.min.css', '.bundle.js', '.map', '*-min.js', '*-min.css'
}

# Artifact classification patterns
ARTIFACT_PATTERNS = {
    "documentation": [
        r"README(\.(md|rst|txt))?$",
        r"CONTRIBUTING(\.(md|rst|txt))?$",
        r"CHANGELOG(\.(md|rst|txt))?$",
        r"CHANGES(\.(md|rst|txt))?$",
        r"HISTORY(\.(md|rst|txt))?$",
        r"MIGRATION(\.(md|rst|txt))?$",
        r"UPGRADE(\.(md|rst|txt))?$",
        r"ROADMAP(\.(md|rst|txt))?$",
        r"SECURITY(\.(md|rst|txt))?$",
        r"CODE_OF_CONDUCT(\.(md|rst|txt))?$",
        r"ARCHITECTURE(\.(md|rst|txt))?$",
        r"AUTHORS(\.(md|rst|txt))?$",
        r"docs?/.*\.(md|rst|txt|html)$",
        r"documentation/.*\.(md|rst|txt|html)$",
        r"wiki/.*$",
        r"guides?/.*\.(md|rst|txt)$",
        r".*\.(md|rst|adoc)$",
    ],
    "test": [
        r"tests?/.*\.(py|js|ts|jsx|tsx|java|go|rs|rb|php|cs|cpp|c)$",
        r"spec/.*\.(py|js|ts|jsx|tsx|rb)$",
        r"__tests__/.*\.(js|ts|tsx|jsx)$",
        r"test_.*\.py$",
        r".*_test\.py$",
        r".*\.test\.(js|ts|tsx|jsx)$",
        r".*\.spec\.(js|ts|tsx|jsx)$",
        r".*Test\.java$",
        r".*_test\.go$",
        r".*_test\.rs$",
        r"conftest\.py$",
        r"pytest\.ini$",
        r"jest\.config\.(js|ts|json)$",
        r"vitest\.config\.(js|ts)$",
    ],
    "dependency": [
        r"requirements.*\.txt$",
        r"setup\.py$",
        r"setup\.cfg$",
        r"pyproject\.toml$",
        r"Pipfile(\.lock)?$",
        r"poetry\.lock$",
        r"conda.*\.ya?ml$",
        r"package\.json$",
        r"package-lock\.json$",
        r"yarn\.lock$",
        r"pnpm-lock\.yaml$",
        r"go\.mod$",
        r"go\.sum$",
        r"Cargo\.toml$",
        r"Cargo\.lock$",
        r"pom\.xml$",
        r"build\.gradle(\.kts)?$",
        r"Gemfile(\.lock)?$",
        r"composer\.json$",
        r"composer\.lock$",
        r"mix\.exs$",
    ],
    "api_specification": [
        r"openapi\.(ya?ml|json)$",
        r"swagger\.(ya?ml|json)$",
        r"api-spec\.(ya?ml|json)$",
        r"api_spec\.(ya?ml|json)$",
        r"api/.*openapi\.(ya?ml|json)$",
        r"api/.*swagger\.(ya?ml|json)$",
        r"docs/api.*\.(ya?ml|json)$",
        r"schema\.(graphql|gql|json)$",
        r".*\.(graphql|gql)$",
        r".*\.proto$",
    ],
    "ci_configuration": [
        r"\.github/workflows/.*\.ya?ml$",
        r"\.travis\.ya?ml$",
        r"\.circleci/.*$",
        r"Jenkinsfile$",
        r"\.gitlab-ci\.ya?ml$",
        r"azure-pipelines\.ya?ml$",
        r"\.drone\.ya?ml$",
        r"\.buildkite/.*$",
        r"appveyor\.ya?ml$",
        r"codecov\.ya?ml$",
    ],
    "docker_configuration": [
        r"Dockerfile.*$",
        r"\.dockerignore$",
        r"docker-compose.*\.ya?ml$",
        r"compose.*\.ya?ml$",
        r"docker/.*$",
    ],
    "deployment_configuration": [
        r"charts/.*$",
        r"helm/.*$",
        r"k8s/.*$",
        r"kubernetes/.*$",
        r"deploy/.*$",
        r"manifests/.*$",
        r"config/crd/.*$",
        r"config/rbac/.*$",
        r"config/manager/.*$",
        r".*\.(tf|tfvars)$",
    ],
    "build_configuration": [
        r"Makefile$",
        r"CMakeLists\.txt$",
        r"tsconfig.*\.json$",
        r"webpack\.config\.(js|ts)$",
        r"vite\.config\.(js|ts)$",
        r"rollup\.config\.(js|ts)$",
        r"babel\.config\.(js|json)$",
        r"\.babelrc$",
        r"gulpfile\.(js|ts)$",
        r"Gruntfile\.(js|ts)$",
        r"tox\.ini$",
        r"noxfile\.py$",
        r"\.eslintrc(\.(js|json|ya?ml))?$",
        r"\.prettierrc(\.(js|json|ya?ml))?$",
        r"\.golangci\.(ya?ml|toml|json)$",
        r"\.yamllint(\.(ya?ml|json))?$",
        r"commitlint\.config\.(js|mjs|ts|json)$",
        r"\.editorconfig$",
        r"Procfile$",
        r"Taskfile\.ya?ml$",
        r".*\.(sh|bash|zsh)$",
    ],
    "other_configuration": [
        r"\.env(\.example|\.template|\.sample|\.local)?$",
        r"config/.*\.(ya?ml|json|toml|ini|cfg)$",
        r"settings\.(py|json|ya?ml|toml)$",
        r"\.gitignore$",
        r"\.gitattributes$",
        r"LICENSE.*$",
        r"COPYING.*$",
        r".*\.(yaml|yml|json|toml|ini|cfg)$",
    ],
}

# Source code extensions
SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs",
    ".rb", ".php", ".cs", ".cpp", ".c", ".h", ".hpp", ".swift",
    ".kt", ".scala", ".ex", ".exs", ".clj", ".jl", ".hs",
}

# Compiled patterns cache
_compiled_patterns = {}


def _get_compiled_patterns():
    """Compile and cache regex patterns."""
    global _compiled_patterns
    if not _compiled_patterns:
        for artifact_type, patterns in ARTIFACT_PATTERNS.items():
            _compiled_patterns[artifact_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
    return _compiled_patterns


def is_ignored_path(filepath: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a file should be ignored with an explicit reason.

    Returns:
        (is_ignored, reason)
    """
    norm_path = filepath.replace("\\", "/")
    parts = norm_path.split("/")
    filename = parts[-1]
    ext = Path(filename).suffix.lower()

    # Check vendor/generated/cache directory names
    for part in parts[:-1]:
        if part.lower() in IGNORED_DIR_NAMES or any(part.lower().endswith(suffix) for suffix in ['.egg-info', '_cache']):
            return True, f"Vendor/generated/cache directory: {part}"

    # Minified files and sourcemaps
    for min_pat in IGNORED_MINIFIED_PATTERNS:
        if min_pat.startswith("*") and filename.endswith(min_pat[1:]):
            return True, "Minified / bundle asset"
        elif filename.endswith(min_pat):
            return True, "Minified / source-map asset"

    # Binary / media file extensions
    if ext in IGNORED_BINARY_EXTENSIONS:
        return True, f"Binary/media format: {ext}"

    return False, None


def classify_file(filepath: str) -> str:
    """
    Classify a file path into an artifact category.

    Args:
        filepath: Relative file path within a repository (e.g., "src/main.py")

    Returns:
        Artifact type string
    """
    patterns = _get_compiled_patterns()
    filepath = filepath.replace("\\", "/")

    # Check against all artifact patterns in priority order
    for artifact_type, compiled in patterns.items():
        for pattern in compiled:
            if pattern.search(filepath):
                return artifact_type

    # Fall back to source code check by extension
    ext = "." + filepath.rsplit(".", 1)[-1].lower() if "." in filepath else ""
    if ext in SOURCE_EXTENSIONS:
        return "source_code"

    return "other"


def get_file_type_description(filepath: str, category: str) -> str:
    """Human-readable description for a file."""
    ext = Path(filepath).suffix.lower()
    ext_map = {
        '.py': 'Python Source',
        '.go': 'Go Source',
        '.js': 'JavaScript Source',
        '.ts': 'TypeScript Source',
        '.tsx': 'React TSX Source',
        '.jsx': 'React JSX Source',
        '.java': 'Java Source',
        '.rs': 'Rust Source',
        '.rb': 'Ruby Source',
        '.php': 'PHP Source',
        '.c': 'C Source',
        '.cpp': 'C++ Source',
        '.cs': 'C# Source',
        '.md': 'Markdown Documentation',
        '.rst': 'reStructuredText Documentation',
        '.yaml': 'YAML Configuration',
        '.yml': 'YAML Configuration',
        '.json': 'JSON Configuration / Data',
        '.toml': 'TOML Configuration',
        '.sh': 'Shell Script',
        '.bash': 'Bash Script',
        '.dockerfile': 'Docker Container Spec',
    }
    if ext in ext_map:
        return ext_map[ext]
    if category != "other":
        return category.replace("_", " ").title()
    return f"{ext[1:].upper() if ext else 'Generic'} File"


def get_artifact_pairs_to_check(artifact_types: list) -> list:
    """
    Return meaningful pairs to check for drift based on present artifact types.
    """
    pairs = []
    type_set = set(artifact_types)

    pair_rules = [
        ("dependency", "source_code", "dependency_vs_code"),
        ("test", "source_code", "test_vs_code"),
        ("documentation", "source_code", "documentation_vs_code"),
        ("api_specification", "source_code", "api_spec_vs_code"),
        ("ci_configuration", "source_code", "ci_vs_project"),
        ("ci_configuration", "dependency", "ci_vs_project"),
        ("docker_configuration", "dependency", "docker_vs_project"),
        ("docker_configuration", "source_code", "docker_vs_project"),
        ("deployment_configuration", "source_code", "deployment_vs_code"),
        ("deployment_configuration", "other_configuration", "deployment_vs_config"),
        ("build_configuration", "source_code", "build_config_vs_project"),
        ("other_configuration", "source_code", "config_vs_code"),
    ]

    for type_a, type_b, drift_category in pair_rules:
        if type_a in type_set and type_b in type_set:
            pairs.append((type_a, type_b, drift_category))

    return pairs
