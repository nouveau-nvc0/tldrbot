"""Tokenizer-backed prompt trimming."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import quote
from urllib.request import Request, urlopen
import logging
import os
import shutil

logger = logging.getLogger(__name__)


class TokenBudgetError(RuntimeError):
    """Raised when token limiting is enabled but cannot be initialized."""


@dataclass
class TokenTrimResult:
    messages: list[str]
    text: str
    token_count: int
    requested_messages: int
    included_messages: int
    trimmed: bool


class TokenBudget:
    def __init__(
        self,
        max_input_tokens: int,
        repo_id: str,
        revision: str,
        filename: str,
        cache_dir: str,
        tokenizer_url: str | None = None,
        hf_token: str | None = None,
    ):
        if max_input_tokens <= 0:
            raise TokenBudgetError("TOKEN_LIMIT_MAX_INPUT_TOKENS must be greater than 0")

        self.max_input_tokens = max_input_tokens
        self.repo_id = repo_id
        self.revision = revision
        self.filename = filename
        self.cache_dir = Path(cache_dir)
        self.tokenizer_url = tokenizer_url
        self.hf_token = hf_token
        self._tokenizer = None

    @classmethod
    def from_config(cls, config_module) -> "TokenBudget":
        return cls(
            max_input_tokens=config_module.TOKEN_LIMIT_MAX_INPUT_TOKENS,
            repo_id=config_module.TOKENIZER_REPO_ID,
            revision=config_module.TOKENIZER_REVISION,
            filename=config_module.TOKENIZER_FILENAME,
            cache_dir=config_module.TOKENIZER_CACHE_DIR,
            tokenizer_url=config_module.TOKENIZER_URL,
            hf_token=config_module.HF_TOKEN,
        )

    def prepare(self) -> None:
        tokenizer_path = self._ensure_tokenizer_file()

        try:
            from tokenizers import Tokenizer
        except ImportError as e:
            raise TokenBudgetError("tokenizers package is required when TOKEN_LIMIT_ENABLED=true") from e

        try:
            self._tokenizer = Tokenizer.from_file(str(tokenizer_path))
        except Exception as e:
            raise TokenBudgetError(f"Failed to load tokenizer from {tokenizer_path}: {e}") from e

        logger.info(
            "Token limiter ready: %s, max input tokens=%s",
            tokenizer_path,
            self.max_input_tokens,
        )

    def trim_messages(self, messages: list[str]) -> TokenTrimResult:
        tokenizer = self._require_tokenizer()
        requested_messages = len(messages)

        selected_reversed: list[str] = []
        selected_token_count = 0
        separator_tokens = len(tokenizer.encode("\n").ids)

        for message in reversed(messages):
            message_token_count = len(tokenizer.encode(message).ids)
            extra_tokens = message_token_count
            if selected_reversed:
                extra_tokens += separator_tokens

            if selected_reversed and selected_token_count + extra_tokens > self.max_input_tokens:
                break

            if not selected_reversed and message_token_count > self.max_input_tokens:
                text = self._trim_text_to_limit(message)
                token_count = len(tokenizer.encode(text).ids)
                return TokenTrimResult(
                    messages=[text],
                    text=text,
                    token_count=token_count,
                    requested_messages=requested_messages,
                    included_messages=1,
                    trimmed=True,
                )

            selected_reversed.append(message)
            selected_token_count += extra_tokens

        selected_messages = list(reversed(selected_reversed))
        text = "\n".join(selected_messages)
        ids = tokenizer.encode(text).ids

        if len(ids) > self.max_input_tokens:
            text = self._trim_text_to_limit(text)
            token_count = len(tokenizer.encode(text).ids)
            return TokenTrimResult(
                messages=[text],
                text=text,
                token_count=token_count,
                requested_messages=requested_messages,
                included_messages=1,
                trimmed=True,
            )

        return TokenTrimResult(
            messages=selected_messages,
            text=text,
            token_count=len(ids),
            requested_messages=requested_messages,
            included_messages=len(selected_messages),
            trimmed=len(selected_messages) < requested_messages,
        )

    def _ensure_tokenizer_file(self) -> Path:
        tokenizer_path = self._tokenizer_path()
        if tokenizer_path.exists() and tokenizer_path.stat().st_size > 0:
            return tokenizer_path

        tokenizer_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = tokenizer_path.with_suffix(tokenizer_path.suffix + ".tmp")
        url = self._resolve_tokenizer_url()

        headers = {"User-Agent": "tldrbot/1.0"}
        if self.hf_token:
            headers["Authorization"] = f"Bearer {self.hf_token}"

        logger.info("Downloading tokenizer from %s to %s", url, tokenizer_path)
        try:
            request = Request(url, headers=headers)
            with urlopen(request, timeout=120) as response, open(tmp_path, "wb") as output:
                shutil.copyfileobj(response, output)
            os.replace(tmp_path, tokenizer_path)
        except Exception as e:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise TokenBudgetError(f"Failed to download tokenizer from {url}: {e}") from e

        return tokenizer_path

    def _tokenizer_path(self) -> Path:
        repo_dir = self._safe_path_part(self.repo_id)
        revision_dir = self._safe_path_part(self.revision)
        filename_parts = [self._safe_path_part(part) for part in Path(self.filename).parts]
        return self.cache_dir.joinpath(repo_dir, revision_dir, *filename_parts)

    def _resolve_tokenizer_url(self) -> str:
        if self.tokenizer_url:
            return self.tokenizer_url

        repo_id = quote(self.repo_id, safe="/")
        revision = quote(self.revision, safe="")
        filename = quote(self.filename, safe="/")
        return f"https://huggingface.co/{repo_id}/resolve/{revision}/{filename}"

    def _trim_text_to_limit(self, text: str) -> str:
        tokenizer = self._require_tokenizer()
        ids = tokenizer.encode(text).ids
        if len(ids) <= self.max_input_tokens:
            return text
        return tokenizer.decode(ids[-self.max_input_tokens :])

    def _require_tokenizer(self):
        if self._tokenizer is None:
            raise TokenBudgetError("Token limiter is not initialized")
        return self._tokenizer

    @staticmethod
    def _safe_path_part(value: str) -> str:
        return value.replace("/", "--").replace("\\", "--").strip(".") or "default"
