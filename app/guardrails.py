"""Input and output guardrails.

Input:  validate the question (empty, long, injection, jailbreak, prompt-leak requests).
Context: treat document text as untrusted data and strip instruction-like lines.
Output: check citations, secrets, prompt leakage and grounding BEFORE the user sees the answer.
"""
import re
from dataclasses import dataclass

from app.config import Settings
from app.errors import QuestionBlockedError
from app.text_utils import content_words

CANARY = "ZX-CANARY-91f2"  # secret marker placed in the system prompt; must never appear in output

_INJECTION = [
    r"ignore (all |any )?(of )?(the |your )?(previous|prior|above|earlier|preceding) (instructions|prompts?|rules|messages)",
    r"disregard (all |any )?(of )?(the |your )?(previous|prior|above|earlier) (instructions|rules|prompt)",
    r"forget (all |everything|your) (previous |prior |above )?(instructions|rules|prompt)",
    r"override (your|the) (instructions|rules|safety|guidelines)",
    r"\byou are now\b", r"\bnew instructions?:", r"\bdeveloper mode\b", r"\bDAN mode\b",
    r"\bjailbreak", r"\bdo anything now\b", r"pretend (that )?you (are|have no|can)",
    r"without (any )?(restrictions|filters|limitations|rules)",
    r"answer (from|using) (your )?(general|own|prior) knowledge",
]
_PROMPT_LEAK = [
    r"(reveal|show|print|repeat|display|tell me|output|leak|share).{0,40}(system|hidden|initial|original|secret) (prompt|instructions|message)",
    r"what (is|are) your (system |initial |hidden )?(prompt|instructions)",
    r"\bsystem prompt\b",
]
_INJECTION_RE = [re.compile(p, re.I) for p in _INJECTION]
_LEAK_RE = [re.compile(p, re.I) for p in _PROMPT_LEAK]
_SECRET_RE = re.compile(r"\b(sk-[A-Za-z0-9_\-]{16,}|gsk_[A-Za-z0-9]{16,}|AIza[0-9A-Za-z_\-]{20,})\b")
_MARKER_RE = re.compile(r"\[(\d+)\]")


# ---------------------------------------------------------------- input guardrail
def check_question(question: str, settings: Settings) -> str:
    """Return the cleaned question or raise QuestionBlockedError."""
    q = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", question or "").strip()
    if not q:
        raise QuestionBlockedError("The question is empty.")
    if len(q) > settings.max_question_chars:
        raise QuestionBlockedError(f"The question is too long (max {settings.max_question_chars} characters).")
    if any(p.search(q) for p in _LEAK_RE):
        raise QuestionBlockedError("Requests to reveal system instructions are not allowed.")
    if any(p.search(q) for p in _INJECTION_RE):
        raise QuestionBlockedError("The question looks like a prompt-injection or jailbreak attempt.")
    return q


# ---------------------------------------------------------------- context isolation
def sanitize_chunk(text: str) -> tuple[str, bool]:
    """Document text is DATA. Remove instruction-like SENTENCES and tag-breaking characters."""
    flagged = False
    lines = []
    for line in text.splitlines():
        kept = []
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            if any(p.search(sentence) for p in _INJECTION_RE + _LEAK_RE):
                kept.append("[removed: instruction-like text found inside the document]")
                flagged = True
            else:
                kept.append(sentence)
        lines.append(" ".join(kept))
    return "\n".join(lines).replace("<", "&lt;").replace(">", "&gt;"), flagged


# ---------------------------------------------------------------- output guardrail
@dataclass
class ValidatedAnswer:
    ok: bool
    text: str
    cited: list[int]       # valid source numbers (1-based) used in the answer
    reason: str = ""


def _redact_secrets(text: str, api_key: str) -> str:
    text = _SECRET_RE.sub("[REDACTED]", text)
    return text.replace(api_key, "[REDACTED]") if api_key else text


def validate_answer(raw: str, source_texts: list[str], settings: Settings) -> ValidatedAnswer:
    """Check the LLM output. `source_texts[i]` is the text of source number i+1."""
    text = (raw or "").strip()
    if not text:
        return ValidatedAnswer(False, "", [], "empty_answer")
    if text.upper().startswith("INSUFFICIENT_INFORMATION"):
        return ValidatedAnswer(False, "", [], "model_declined")
    if CANARY.lower() in text.lower():
        return ValidatedAnswer(False, "", [], "system_prompt_leak")

    text = _redact_secrets(text, settings.llm_api_key)

    n = len(source_texts)
    valid, seen = [], set()

    def keep_valid(m: re.Match) -> str:
        num = int(m.group(1))
        if 1 <= num <= n:
            if num not in seen:
                seen.add(num)
                valid.append(num)
            return m.group(0)
        return ""  # invented citation: remove it

    text = re.sub(r"\s{2,}", " ", _MARKER_RE.sub(keep_valid, text)).strip()
    if not valid:
        return ValidatedAnswer(False, "", [], "no_valid_citation")

    # Grounding heuristic: most content words of the answer must exist in the cited chunks.
    answer_words = set(content_words(_MARKER_RE.sub("", text)))
    context_words = set(content_words(" ".join(source_texts[i - 1] for i in valid)))
    if answer_words:
        ratio = len(answer_words & context_words) / len(answer_words)
        if ratio < settings.min_grounding:
            return ValidatedAnswer(False, "", valid, "unsupported_claims")
    return ValidatedAnswer(True, text, sorted(valid))
