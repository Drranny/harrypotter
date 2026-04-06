import time
import os

# ─── 모드 감지 ───────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
USE_GEMINI = bool(GEMINI_API_KEY)
USE_OPENAI = bool(OPENAI_API_KEY)

if USE_OPENAI:
    from openai import OpenAI
    _openai_client = OpenAI(api_key=OPENAI_API_KEY)
    print("[INFO] LLM Backend: OpenAI GPT-4o-mini (API)")
elif USE_GEMINI:
    from google import genai
    _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    print("[INFO] LLM Backend: Gemini (API)")
else:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
    import transformers.dynamic_module_utils as dynamic_module_utils

    MODEL_ID = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"
    MODEL_REVISION = "e949c91dec92095908d34e6b560af77dd0c993f8"
    MODEL_CACHE_DIR = os.path.expanduser(
        "~/.cache/huggingface/hub/models--LGAI-EXAONE--EXAONE-3.5-2.4B-Instruct/snapshots/"
        + MODEL_REVISION
    )
    MODEL_SOURCE = MODEL_CACHE_DIR if os.path.isdir(MODEL_CACHE_DIR) else MODEL_ID
    HF_MODULES_CACHE = os.environ.get("HF_MODULES_CACHE", "/tmp/hf_modules_cache")
    os.environ["HF_MODULES_CACHE"] = HF_MODULES_CACHE
    os.makedirs(HF_MODULES_CACHE, exist_ok=True)
    dynamic_module_utils.HF_MODULES_CACHE = HF_MODULES_CACHE

    print(f"[INFO] Loading Language Model: {MODEL_ID}")
    print("[INFO] Infrastructure: CPU-Optimized (16 Cores)")

    tokenizer = None
    model = None
    pipe = None

    def _ensure_pipeline():
        global tokenizer, model, pipe
        if pipe is not None:
            return tokenizer, model, pipe
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_SOURCE, revision=MODEL_REVISION, local_files_only=True,
        )
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_SOURCE,
            revision=MODEL_REVISION,
            code_revision=MODEL_REVISION,
            torch_dtype=torch.bfloat16,
            device_map="cpu",
            trust_remote_code=True,
            local_files_only=True,
        )
        pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)
        return tokenizer, model, pipe

def _generate_openai(prompt: str) -> dict:
    time.sleep(1)  # 짧은 딜레이
    start = time.perf_counter()
    try:
        response = _openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert Python Backend Developer. "
                        "Answer concisely in English using only the provided context."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.3,
        )
        text = response.choices[0].message.content or ""
    except Exception as e:
        print(f"[WARN] OpenAI API error: {e}, retrying in 10s...")
        time.sleep(10)
        response = _openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Answer using only the provided context."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.3,
        )
        text = response.choices[0].message.content or ""
    elapsed = time.perf_counter() - start
    print(f"[DEBUG] OpenAI Latency: {elapsed:.2f}s")
    return {
        "response": text,
        "full_generated_text": text,
        "prompt_token_count": 0,
        "response_token_count": len(text.split()),
        "latency_sec": float(elapsed),
        "throughput_tokens_per_sec": 0.0,
        "model_id": "gpt-4o-mini",
        "model_revision": "api",
    }
    
def _generate_gemini(prompt: str) -> dict:
    max_retries = 5  # 최대 5번까지 재시도
    wait_time = 4    # 기본 4초 대기 (무료 티어 보호용)
    start = time.perf_counter()
    for attempt in range(max_retries):
        try:
            # 1. 기본적으로 요청 전 대기
            time.sleep(wait_time)
            
            # 2. API 호출
            response = _gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            text = response.text
            
            # 3. 성공 시 지연 시간 측정 후 반환
            elapsed = time.perf_counter() - start
            print(f"[DEBUG] Gemini Latency: {elapsed:.2f}s")

            return {
                "response": text,
                "full_generated_text": text,
                "prompt_token_count": 0,
                "response_token_count": len(text.split()),
                "latency_sec": float(elapsed),
                "throughput_tokens_per_sec": 0.0,
                "model_id": "gemini-2.5-flash",
                "model_revision": "api",
            }
        except Exception as e:
                # 4. 실패 시 경고 출력 및 대기 시간 2배 증가 (4초 -> 8초 -> 16초...)
                print(f"[WARN] Gemini API error: {e}")
                print(f"[WARN] Retrying in {wait_time * 2}s... (Attempt {attempt + 1}/{max_retries})")
                wait_time *= 2 
            
    # 5. 5번 모두 실패했을 경우 스크립트가 터지지 않도록 빈 값 반환
    print("[ERROR] Max retries reached. Returning empty response to prevent crash.")
    return {
        "response": "",
        "full_generated_text": ""
    }

def _generate_exaone(prompt: str, answer_language: str = "English") -> dict:
    """기존 EXAONE 로컬 추론"""
    tokenizer, _, pipe = _ensure_pipeline()
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert Python Backend Developer and AI assistant. "
                f"Answer concisely in {answer_language} using only the provided context."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    input_text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    input_ids = tokenizer.encode(input_text, return_tensors="pt")
    input_token_count = input_ids.shape[1]

    print(f"[DEBUG] Prompt Token Count: {input_token_count}")
    print("[DEBUG] Local Inference in Progress...")

    start = time.perf_counter()
    outputs = pipe(input_text, max_new_tokens=300, do_sample=True, temperature=0.3, top_p=0.9)
    elapsed = time.perf_counter() - start

    full_output = outputs[0]["generated_text"]
    response = full_output.split("[|assistant|]")[-1].strip()
    output_token_count = len(tokenizer.encode(response))
    throughput = 0.0 if elapsed <= 0 else output_token_count / elapsed

    print(f"[DEBUG] Latency: {elapsed:.2f}s | Throughput: {throughput:.2f} tokens/s")

    return {
        "response": response,
        "full_generated_text": full_output,
        "prompt_token_count": int(input_token_count),
        "response_token_count": int(output_token_count),
        "latency_sec": float(elapsed),
        "throughput_tokens_per_sec": float(throughput),
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
    }


def generate_with_meta(prompt: str, answer_language: str = "English") -> dict:
    if USE_OPENAI:
        return _generate_openai(prompt)
    elif USE_GEMINI:
        return _generate_gemini(prompt)
    else:
        return _generate_exaone(prompt, answer_language)


def rag_answer(prompt: str, answer_language: str = "English") -> str:
    return generate_with_meta(prompt, answer_language)["response"]