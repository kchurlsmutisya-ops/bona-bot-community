import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


_MODEL_ID = re.compile(r"[A-Za-z0-9._-]{1,128}\Z")
_MAX_REQUEST_BYTES = 1024 * 1024
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_SYSTEM_INSTRUCTION = (
    "You are a coding assistant. You cannot access or change local files or "
    "execute commands. Only use information the user explicitly supplies. "
    "Do not claim to have run commands or changed files. Keep security help "
    "defensive and limited to authorized work."
)


class GeminiError(RuntimeError):
    """A safe, user-facing Gemini API error."""


class GeminiClient:
    def __init__(self, timeout_seconds: float = 60):
        self.timeout_seconds = timeout_seconds

    def generate(self, api_key: str, model: str, contents: list[dict[str, Any]]) -> str:
        key = api_key.strip()
        model_id = model.strip()
        if not key:
            raise GeminiError("Enter a Gemini API key.")
        if "\r" in key or "\n" in key:
            raise GeminiError("The API key contains invalid characters.")
        if not _MODEL_ID.fullmatch(model_id):
            raise GeminiError("Enter a valid Gemini model ID.")
        if not contents:
            raise GeminiError("Enter a prompt before sending.")

        body = json.dumps(
            {
                "systemInstruction": {"parts": [{"text": _SYSTEM_INSTRUCTION}]},
                "contents": contents,
                "generationConfig": {"temperature": 0.2},
            },
            ensure_ascii=False,
        ).encode("utf-8")
        if len(body) > _MAX_REQUEST_BYTES:
            raise GeminiError("The conversation is too large; start a new chat.")

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{quote(model_id, safe='')}:generateContent"
        )
        request = Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": key,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_response = response.read(_MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            raise GeminiError(f"Gemini returned HTTP {exc.code}. Check the key and model.") from None
        except (URLError, TimeoutError, OSError):
            raise GeminiError("Could not reach Gemini. Check the connection and try again.") from None

        if len(raw_response) > _MAX_RESPONSE_BYTES:
            raise GeminiError("Gemini's response was too large to display.")
        try:
            payload = json.loads(raw_response)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise GeminiError("Gemini returned an invalid response.") from None

        if not isinstance(payload, dict):
            raise GeminiError("Gemini returned an invalid response.")
        candidates = payload.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise GeminiError("Gemini returned no text for this prompt.")
        first_candidate = candidates[0]
        if not isinstance(first_candidate, dict):
            raise GeminiError("Gemini returned an invalid response.")
        content = first_candidate.get("content")
        if not isinstance(content, dict):
            raise GeminiError("Gemini returned an invalid response.")
        parts = content.get("parts", [])
        if not isinstance(parts, list):
            raise GeminiError("Gemini returned an invalid response.")
        answer = "".join(
            part["text"]
            for part in parts
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        ).strip()
        if not answer:
            raise GeminiError("Gemini returned no text for this prompt.")
        return answer
