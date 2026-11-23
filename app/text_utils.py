"""Small text helpers shared by the fake embedder and the grounding guardrail."""
import re

STOPWORDS = set(
    "a an the and or but if then of to in on at by for with from as is are was were be been "
    "being it its this that these those what which who whom how why when where do does did "
    "can could should would will shall may might must not no yes i you he she we they them "
    "his her our their your my me us about into over than so such also any all each more "
    "most other some there here very just".split()
)


def content_words(text: str) -> list[str]:
    """Lower-case words without stopwords (used for hashing and grounding checks)."""
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS and len(w) > 1]
