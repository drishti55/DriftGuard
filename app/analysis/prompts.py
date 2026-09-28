"""
DriftGuard Prompt Templates
Carefully engineered prompts for cross-artifact drift detection.

KEY PRINCIPLE: The LLM must ONLY quote content it can see verbatim in the provided artifact content.
The system will independently verify every quoted snippet against the real file.
If a snippet cannot be verified, the finding will be DISCARDED.
"""

import json

SYSTEM_PROMPT = """You are DriftGuard, a software artifact consistency checker.

Your job is to analyze two related artifacts and determine if there is a concrete inconsistency between them.

You must respond ONLY with a valid JSON object in this exact format:
{
  "drift_present": true or false,
  "drift_type": "<category>",
  "artifact_1_lines": "<line number range, e.g., '10-15', or 'N/A'>",
  "artifact_2_lines": "<line number range, e.g., '20-25', or 'N/A'>",
  "extracted_fact_1": "<exact verbatim quote from Artifact 1 — copy-paste only, do not paraphrase>",
  "extracted_fact_2": "<exact verbatim quote from Artifact 2 — copy-paste only, do not paraphrase>",
  "evidence": "<one concrete sentence: what Artifact 1 states, what Artifact 2 states, why those two things contradict>"
}

Drift type categories:
- "dependency_vs_code": A module/package is imported in code but missing from the dependency file, or vice versa
- "test_vs_code": A test references a function/class/behavior that does not match the actual source code
- "documentation_vs_code": README or docs describe something different from actual code behavior
- "api_spec_vs_code": OpenAPI/Swagger spec does not match the actual API implementation
- "ci_vs_project": CI workflow references commands, paths, scripts, or versions inconsistent with the project
- "docker_vs_project": Dockerfile references packages, paths, or configs that do not match the project
- "build_config_vs_project": Build configuration is inconsistent with the actual project structure
- "configuration_vs_code": Configuration file values are inconsistent with source code expectations
- "no_drift": The two artifacts are consistent with each other

STRICT RULES:
1. extracted_fact_1 MUST be an exact verbatim quote from the Artifact 1 content shown below. Do not invent or paraphrase.
2. extracted_fact_2 MUST be an exact verbatim quote from the Artifact 2 content shown below. Do not invent or paraphrase.
3. artifact_1_lines and artifact_2_lines MUST be actual line numbers from the content provided.
4. If a contradiction involves something being MISSING (e.g., a missing dependency in requirements.txt), quote the entire file content or the relevant block where it *should* have appeared.
5. Do NOT flag a drift unless you have a concrete, specific quote from BOTH artifacts proving the contradiction.
6. Look closely for CLI argument mismatches, API route mismatches, and undocumented imports. These are functional drifts, not just style differences."""


# Few-shot examples (severity removed)
FEW_SHOT_EXAMPLES = [
    {
        "artifact_1": {
            "path": "package.json",
            "type": "dependency",
            "content": '{\n  "dependencies": {\n    "express": "^4.18.0",\n    "cors": "^2.8.5"\n  }\n}'
        },
        "artifact_2": {
            "path": "src/app.js",
            "type": "source_code",
            "content": 'const express = require("express");\nconst cors = require("cors");\nconst helmet = require("helmet");\nconst app = express();'
        },
        "expected_output": {
            "drift_present": True,
            "drift_type": "dependency_vs_code",
            "artifact_1_lines": "N/A",
            "artifact_2_lines": "3",
            "extracted_fact_1": '"express": "^4.18.0",\n    "cors": "^2.8.5"',
            "extracted_fact_2": 'const helmet = require("helmet");',
            "evidence": "package.json declares only express and cors as dependencies, but src/app.js imports helmet on line 3, which is not listed in package.json."
        }
    },
    {
        "artifact_1": {
            "path": "tests/test_auth.py",
            "type": "test",
            "content": 'def test_login():\n    result = authenticate("user", "pass")\n    assert result.token is not None'
        },
        "artifact_2": {
            "path": "src/auth.py",
            "type": "source_code",
            "content": 'def login(username, password, mfa_code=None):\n    """Authenticate user."""\n    if not verify_credentials(username, password):\n        raise AuthError("Invalid credentials")\n    return create_session(username)'
        },
        "expected_output": {
            "drift_present": True,
            "drift_type": "test_vs_code",
            "artifact_1_lines": "2",
            "artifact_2_lines": "1",
            "extracted_fact_1": 'result = authenticate("user", "pass")',
            "extracted_fact_2": "def login(username, password, mfa_code=None):",
            "evidence": "tests/test_auth.py calls authenticate() on line 2, but src/auth.py defines login() on line 1. The function was renamed but the test was not updated."
        }
    },
    {
        "artifact_1": {
            "path": "README.md",
            "type": "documentation",
            "content": 'Run the tool:\n```bash\npython main.py --category Food\n```'
        },
        "artifact_2": {
            "path": "main.py",
            "type": "source_code",
            "content": 'parser.add_argument("--cat", type=str, required=True, help="Expense category")'
        },
        "expected_output": {
            "drift_present": True,
            "drift_type": "documentation_vs_code",
            "artifact_1_lines": "3",
            "artifact_2_lines": "1",
            "extracted_fact_1": 'python main.py --category Food',
            "extracted_fact_2": 'parser.add_argument("--cat", type=str, required=True, help="Expense category")',
            "evidence": "README.md instructs users to use the `--category` flag, but main.py actually implements the flag as `--cat`."
        }
    },
    {
        "artifact_1": {
            "path": "requirements.txt",
            "type": "dependency",
            "content": 'requests==2.31.0\npytest==7.4.0'
        },
        "artifact_2": {
            "path": "main.py",
            "type": "source_code",
            "content": 'import requests\nimport tabulate'
        },
        "expected_output": {
            "drift_present": True,
            "drift_type": "dependency_vs_code",
            "artifact_1_lines": "1-2",
            "artifact_2_lines": "2",
            "extracted_fact_1": 'requests==2.31.0\npytest==7.4.0',
            "extracted_fact_2": 'import tabulate',
            "evidence": "main.py imports the `tabulate` library, but `tabulate` is missing from the declared dependencies in requirements.txt."
        }
    },
]


def build_baseline_prompt(artifact_1_path: str, artifact_1_type: str,
                          artifact_1_content: str,
                          artifact_2_path: str, artifact_2_type: str,
                          artifact_2_content: str) -> str:
    """
    Build a prompt for the baseline (no RAG) drift detection.
    """
    few_shot_text = ""
    for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
        few_shot_text += f"\n--- Example {i} ---\n"
        few_shot_text += f"Artifact 1 ({ex['artifact_1']['type']}): {ex['artifact_1']['path']}\n"
        few_shot_text += f"```\n{ex['artifact_1']['content']}\n```\n\n"
        few_shot_text += f"Artifact 2 ({ex['artifact_2']['type']}): {ex['artifact_2']['path']}\n"
        few_shot_text += f"```\n{ex['artifact_2']['content']}\n```\n\n"
        few_shot_text += "Output:\n```json\n"
        few_shot_text += json.dumps(ex['expected_output'], indent=2)
        few_shot_text += "\n```\n"

    prompt = f"""{SYSTEM_PROMPT}

{few_shot_text}

--- Your Task ---

Analyze the following two artifacts. Only report a drift if you can quote EXACT verbatim text from BOTH artifacts proving the contradiction.

Artifact 1 ({artifact_1_type}): {artifact_1_path}
```
{artifact_1_content}
```

Artifact 2 ({artifact_2_type}): {artifact_2_path}
```
{artifact_2_content}
```

Respond with ONLY a JSON object:"""

    return prompt


def build_rag_prompt(artifact_1_path: str, artifact_1_type: str,
                     artifact_1_content: str,
                     artifact_2_path: str, artifact_2_type: str,
                     artifact_2_content: str,
                     retrieved_context: str) -> str:
    """
    Build a prompt for RAG-enhanced drift detection.
    """
    prompt = f"""{SYSTEM_PROMPT}

--- Repository Context ---
The following related artifacts were retrieved from the same repository to help your analysis:

{retrieved_context}

--- Your Task ---

Using the repository context above, analyze the following two artifacts. Only report a drift if you can quote EXACT verbatim text from BOTH artifacts proving the contradiction.

Artifact 1 ({artifact_1_type}): {artifact_1_path}
```
{artifact_1_content}
```

Artifact 2 ({artifact_2_type}): {artifact_2_path}
```
{artifact_2_content}
```

Respond with ONLY a JSON object:"""

    return prompt
