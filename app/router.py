import re
from dataclasses import dataclass

FAST_LOCAL = "fast_local"
SMART_LOCAL = "smart_local"
CODE_EXPERT = "code_expert"
CLOUD = "cloud"

MODEL_MAP = {
    FAST_LOCAL: "qwen2.5:7b",
    SMART_LOCAL: "llama3.2:latest",
    CODE_EXPERT: "qwen2.5-coder:14b",
}

_BROWSER_RE = re.compile(
    r"\b(research|find|look up|search|browse|web|recent|latest|news|website|url|http)\b",
    re.IGNORECASE,
)
_CODE_RE = re.compile(
    r"\b(code|script|program|function|class|implement|build|write a|python|javascript|bash|sql)\b",
    re.IGNORECASE,
)
_FILE_RE = re.compile(
    r"\b(file|document|pdf|csv|excel|spreadsheet|upload|attachment|summarize this|analyze this)\b",
    re.IGNORECASE,
)

_COMPLEX_WORD_THRESHOLD = 80


@dataclass
class RouteDecision:
    model_key: str
    model_name: str
    needs_browser: bool
    needs_code: bool
    needs_file: bool
    is_complex: bool


def classify(prompt: str) -> RouteDecision:
    word_count = len(prompt.split())
    needs_browser = bool(_BROWSER_RE.search(prompt))
    needs_code = bool(_CODE_RE.search(prompt))
    needs_file = bool(_FILE_RE.search(prompt))
    is_complex = word_count > _COMPLEX_WORD_THRESHOLD or (needs_browser and needs_code)

    if needs_code:
        model_key = CODE_EXPERT
    elif needs_browser or needs_file or word_count > 30:
        model_key = SMART_LOCAL
    else:
        model_key = FAST_LOCAL

    return RouteDecision(
        model_key=model_key,
        model_name=MODEL_MAP[model_key],
        needs_browser=needs_browser,
        needs_code=needs_code,
        needs_file=needs_file,
        is_complex=is_complex,
    )
