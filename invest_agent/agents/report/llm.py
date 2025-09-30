from typing import Optional, Callable
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# ----- 로컬 모델 (지연 로딩 추천) -----
_tokenizer = None
_model = None

def _ensure_model(model_name: str = "google/gemma-2b-it"):
    global _tokenizer, _model
    if _tokenizer is None or _model is None:
        _tokenizer = AutoTokenizer.from_pretrained(model_name)
        _model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto"
        )
    return _tokenizer, _model

def local_llm_call(system: str, user: str) -> str:
    tok, mdl = _ensure_model()
    prompt = f"[SYSTEM]\n{system}\n\n[USER]\n{user}\n\n[ASSISTANT]\n"
    inputs = tok(prompt, return_tensors="pt").to(mdl.device)
    with torch.no_grad():
        out = mdl.generate(**inputs, max_new_tokens=200, do_sample=True, temperature=0.7)
    return tok.decode(out[0], skip_special_tokens=True)

def default_llm_refiner(text: str, llm_call: Optional[Callable[[str,str], str]] = None) -> str:
    if not llm_call:
        return text
    system = ("너는 VC 투자 메모 전문 에디터다. 수치/사실/표/차트는 바꾸지 말고, "
              "문장만 간결하고 논리적으로 다듬어라. 한국어 존댓말.")
    user = f"아래 텍스트를 다듬어줘:\n\n{text}"
    try:
        refined = llm_call(system, user)
        return refined or text
    except Exception:
        return text
