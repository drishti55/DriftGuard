"""
DriftGuard LLM Client
Wrapper around Ollama for local LLM inference with retry logic and structured output parsing.
"""

import time
import logging

import httpx
import ollama as ollama_client

from app.analysis.output_validator import validate_output, ParseResult
from app import config

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for LLM inference via OmniRoute with local Ollama fallback."""

    def __init__(self, model: str = None, fallback_model: str = None,
                 timeout: int = None, host: str = None,
                 omniroute_host: str = None, omniroute_api_key: str = None):
        self.model = model or config.DEFAULT_MODEL or config.OLLAMA_MODEL
        self.fallback_model = fallback_model or config.OLLAMA_FALLBACK_MODEL
        self.timeout = timeout or config.OLLAMA_TIMEOUT
        self.host = host or config.OLLAMA_HOST
        self.omniroute_host = omniroute_host or config.OMNIROUTE_HOST
        self.omniroute_api_key = omniroute_api_key or config.OMNIROUTE_API_KEY

        # Track statistics
        self.stats = {
            "total_calls": 0,
            "successful_parses": 0,
            "parse_failures": 0,
            "fallback_used": 0,
            "total_tokens": 0,
            "total_latency_s": 0.0,
        }

        # Initialize Ollama client
        try:
            self.client = ollama_client.Client(host=self.host)
        except Exception:
            self.client = None

    def check_model_available(self, model_name: str) -> bool:
        """Check if a model is available in Ollama."""
        try:
            models = self.client.list()
            available = [m.model for m in models.models]
            for avail in available:
                if avail == model_name or avail == f"{model_name}:latest":
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to check Ollama models: {e}")
            return False

    def generate(self, prompt: str, model: str = None,
                 max_retries: int = 2) -> ParseResult:
        """
        Send a prompt to the LLM and parse the response into a DriftPrediction.

        Args:
            prompt: The full prompt text
            model: Override model name
            max_retries: Number of retries on parse failure

        Returns:
            ParseResult with prediction or error details
        """
        target_model = model or self.model
        self.stats["total_calls"] += 1

        # 1. Try OmniRoute Gateway First
        if self.omniroute_host:
            try:
                start_time = time.time()
                endpoint = f"{self.omniroute_host.rstrip('/')}/chat/completions"
                headers = {"Content-Type": "application/json"}
                if self.omniroute_api_key:
                    headers["Authorization"] = f"Bearer {self.omniroute_api_key}"

                payload = {
                    "model": target_model,
                    "messages": [
                        {"role": "system", "content": "You are DriftGuard Auditor. Output strictly valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.0,
                }
                with httpx.Client(timeout=float(self.timeout or 60)) as http_client:
                    res = http_client.post(endpoint, json=payload, headers=headers)
                    if res.status_code == 200:
                        content = res.json()["choices"][0]["message"]["content"]
                        result = validate_output(content)
                        if result.success:
                            self.stats["successful_parses"] += 1
                            self.stats["total_latency_s"] += (time.time() - start_time)
                            return result
            except Exception as e:
                logger.debug(f"OmniRoute gateway call failed: {e}. Falling back to Ollama.")

        # 2. Local Ollama Fallback
        if not self.client:
            return ParseResult(raw_output="", error="OmniRoute failed and local Ollama client is unavailable")

        for attempt in range(max_retries + 1):
            try:
                start_time = time.time()

                response = self.client.generate(
                    model=target_model,
                    prompt=prompt,
                    format="json",  # Force JSON output
                    options={
                        "temperature": 0.1,  # Low temp for structured output
                        "top_p": 0.9,
                        "num_predict": 1024,  # Allow longer structured output
                    },
                )

                elapsed = time.time() - start_time
                self.stats["total_latency_s"] += elapsed

                raw_output = response.get("response", "")

                # Track token usage if available
                if "eval_count" in response:
                    self.stats["total_tokens"] += response["eval_count"]

                # Validate and parse
                result = validate_output(raw_output)

                if result.success:
                    self.stats["successful_parses"] += 1
                    logger.debug(f"Parse succeeded on attempt {attempt + 1} "
                                 f"({elapsed:.1f}s, method={result.parse_method})")
                    return result

                # Parse failed — retry with a nudge
                if attempt < max_retries:
                    logger.warning(f"Parse failed on attempt {attempt + 1}: {result.error}. Retrying...")
                    # Add a hint to the prompt for retry
                    prompt = prompt.rstrip() + "\n\nIMPORTANT: Respond with ONLY a valid JSON object, no other text."
                    continue

            except Exception as e:
                elapsed = time.time() - start_time if 'start_time' in dir() else 0
                logger.error(f"LLM call failed on attempt {attempt + 1}: {e}")

                if attempt < max_retries:
                    time.sleep(1)
                    continue

                return ParseResult(
                    raw_output="",
                    error=f"LLM call failed: {e}"
                )

        # All retries exhausted — try fallback model
        if target_model != self.fallback_model:
            logger.warning(f"Primary model {target_model} failed. Trying fallback {self.fallback_model}...")
            self.stats["fallback_used"] += 1
            return self.generate(prompt, model=self.fallback_model, max_retries=1)

        # Total failure
        self.stats["parse_failures"] += 1
        return ParseResult(
            raw_output=raw_output if 'raw_output' in dir() else "",
            error="All parse attempts and fallback exhausted"
        )

    def get_stats(self) -> dict:
        """Return inference statistics."""
        stats = dict(self.stats)
        if stats["total_calls"] > 0:
            stats["parse_success_rate"] = stats["successful_parses"] / stats["total_calls"]
            stats["avg_latency_s"] = stats["total_latency_s"] / stats["total_calls"]
        else:
            stats["parse_success_rate"] = 0.0
            stats["avg_latency_s"] = 0.0
        return stats
