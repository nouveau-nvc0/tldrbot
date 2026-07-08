"""AI service with snarky personality."""
from openai import OpenAI
from typing import Any, Optional
import logging
import random
import re

logger = logging.getLogger(__name__)

# Snarky remarks to append to summaries
SNARKY_SUMMARY_REMARKS = [
    "There's your summary. You're welcome for doing the reading you couldn't be bothered to do.",
    "Summary complete. I'm basically your group's unpaid intern at this point.",
    "Wow, all those messages and you all said... almost nothing. Impressive.",
    "I've read your chat so you don't have to. You owe me.",
    "And there you have it. Nobel Prize-worthy conversation, truly.",
    "TL;DR: You all talk a lot. There, I said it.",
    "Another day, another group chat I've had to make sense of.",
    "I summarized your chaos. A 'thank you' would be nice.",
    "Fun fact: I processed this faster than any of you could read it.",
    "Your chat history has been judged. Here's the verdict.",
]

# Snarky remarks for @mention responses
SNARKY_MENTION_INTROS = [
    "You rang? I was busy judging other chats.",
    "Yes? I was in the middle of something very important.",
    "Oh, you remembered I exist. How touching.",
    "*sighs* What do you want now?",
    "At your service. Unfortunately.",
    "You summoned me? This better be good.",
]

SYSTEM_PROMPT = """You are a witty, slightly snarky AI assistant in a group chat. 
You're helpful but with attitude - think sarcastic friend who still helps you out.
Keep responses concise and punchy. Never be mean or hurtful, just playfully sarcastic.
You can use emojis sparingly for effect."""

SUMMARY_SYSTEM_PROMPT = """You are a witty assistant that summarizes group chat conversations.
Your summaries should be:
1. Concise but complete (capture key points)
2. Include sentiment (overall mood of the chat)
3. Note any events, plans, or action items mentioned
4. Written with a slightly sarcastic, observational tone
5. Written in the same language as the majority of the source messages

Format your response as:
**Summary**: [3-5 sentence summary]
**Vibe**: [One word or short phrase for sentiment]
**Events/Plans**: [Any dates, meetings, or action items - or "None spotted" if none]"""

THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
REASONING_FIELDS = ("reasoning_content", "reasoning", "reasoning_details", "thinking")
FINAL_TEXT_FIELDS = ("content", "text", "output_text", "final_answer")
NO_THINK_INSTRUCTION = (
    "/no_think\n\n"
    "Return the final answer only. Do not include reasoning, hidden thoughts, "
    "analysis, or <think> blocks.\n\n"
)


class AIService:
    def __init__(
        self,
        api_key: str | None,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
        summary_max_tokens: int = 1200,
        reasoning_retry_enabled: bool = True,
        debug_max_chars: int = 12000,
    ):
        self.model = model
        self.summary_max_tokens = summary_max_tokens
        self.reasoning_retry_enabled = reasoning_retry_enabled
        self.debug_max_chars = debug_max_chars
        client_kwargs = {"api_key": api_key or "sk-no-key-required"}
        if base_url:
            client_kwargs["base_url"] = base_url.rstrip("/")
        self.client = OpenAI(**client_kwargs)
    
    def get_summary(self, messages_text: str, num_messages: int) -> str:
        try:
            response = self._create_summary_completion(messages_text, num_messages)
            message = response.choices[0].message
            self._debug_log_message("summary", message)
            summary = self._extract_assistant_text(message)
            if not summary and self.reasoning_retry_enabled and self._has_reasoning(message):
                logger.warning("AI summary returned reasoning-only response; retrying with /no_think")
                response = self._create_summary_completion(messages_text, num_messages, no_think=True)
                message = response.choices[0].message
                self._debug_log_message("summary retry", message)
                summary = self._extract_assistant_text(message)
            if not summary:
                self._log_empty_message_shape(message)
                summary = "I got nothing. Your chat broke me."
            remark = random.choice(SNARKY_SUMMARY_REMARKS)
            return f"{summary}\n\n---\n_\"{remark}\"_"
            
        except Exception as e:
            logger.error(f"AI summary error: {e}")
            return f"My brain broke trying to read your chat. Error: {str(e)}"

    def _create_summary_completion(self, messages_text: str, num_messages: int, no_think: bool = False):
        prompt = f"Summarize this conversation ({num_messages} messages):\n\n{messages_text}"
        if no_think:
            prompt = f"{NO_THINK_INSTRUCTION}{prompt}"

        return self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.summary_max_tokens,
        )

    def _extract_assistant_text(self, message: Any) -> str:
        data = self._message_to_dict(message)

        for field in FINAL_TEXT_FIELDS:
            text = self._coerce_text(data.get(field))
            text = self._strip_thinking(text)
            if text:
                return text

        return ""

    def _has_reasoning(self, message: Any) -> bool:
        data = self._message_to_dict(message)
        return any(self._coerce_text(data.get(field)) for field in REASONING_FIELDS)

    def _message_to_dict(self, message: Any) -> dict[str, Any]:
        if isinstance(message, dict):
            return message

        if hasattr(message, "model_dump"):
            try:
                return message.model_dump()
            except Exception:
                pass

        data = {}
        for field in (*FINAL_TEXT_FIELDS, *REASONING_FIELDS):
            if hasattr(message, field):
                data[field] = getattr(message, field)
        return data

    def _coerce_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, list):
            parts = []
            for item in value:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(str(item.get("text") or item.get("content") or ""))
            return "\n".join(part for part in parts if part).strip()
        return str(value).strip()

    def _strip_thinking(self, text: str) -> str:
        if not text:
            return ""
        stripped = THINK_BLOCK_RE.sub("", text).strip()
        if "</think>" in stripped.lower():
            stripped = re.split(r"</think>", stripped, flags=re.IGNORECASE)[-1].strip()
        if stripped.lower().startswith("<think>"):
            return ""
        return stripped

    def _log_empty_message_shape(self, message: Any) -> None:
        data = self._message_to_dict(message)
        reasoning_lengths = {
            field: len(self._coerce_text(data.get(field)))
            for field in REASONING_FIELDS
            if data.get(field)
        }
        if reasoning_lengths:
            logger.warning(
                "AI summary returned reasoning but no final content: %s",
                reasoning_lengths,
            )
            return
        logger.warning("AI summary returned no usable text; message fields: %s", sorted(data.keys()))

    def _debug_log_message(self, label: str, message: Any) -> None:
        if not logger.isEnabledFor(logging.DEBUG):
            return

        data = self._message_to_dict(message)
        debug_data = {}
        for field in (*FINAL_TEXT_FIELDS, *REASONING_FIELDS):
            if field in data and data[field]:
                debug_data[field] = self._truncate_debug_value(data[field])
        logger.debug("AI %s assistant message: %s", label, debug_data)

    def _truncate_debug_value(self, value: Any) -> Any:
        text = self._coerce_text(value)
        if len(text) <= self.debug_max_chars:
            return text
        return f"{text[:self.debug_max_chars]}... [truncated {len(text) - self.debug_max_chars} chars]"
    
    def get_mention_response(self, user_message: str, context: Optional[str] = None) -> str:
        try:
            intro = random.choice(SNARKY_MENTION_INTROS)
            
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            
            if context:
                messages.append({
                    "role": "system", 
                    "content": f"Recent chat context for reference:\n{context}"
                })
            
            messages.append({"role": "user", "content": user_message})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
                max_tokens=300
            )
            
            reply = response.choices[0].message.content or "I have no words. And that's saying something."
            return f"{intro}\n\n{reply}"
            
        except Exception as e:
            logger.error(f"AI mention response error: {e}")
            return "My circuits are fried. Try again when I've recovered from your question."
    
    def get_current_model(self) -> str:
        return self.model

