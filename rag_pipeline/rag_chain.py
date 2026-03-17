import time
import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import transformers.dynamic_module_utils as dynamic_module_utils

# 모델 설정
MODEL_ID = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"
# Pin a known-good model revision to avoid dynamic code/API mismatch.
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
print(f"[INFO] Model Revision: {MODEL_REVISION}")
print("[INFO] Infrastructure: CPU-Optimized (16 Cores)")
print(f"[INFO] Model Source: {MODEL_SOURCE}")

tokenizer = None
model = None
pipe = None


def _ensure_pipeline():
    global tokenizer, model, pipe
    if pipe is not None:
        return tokenizer, model, pipe

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_SOURCE,
        revision=MODEL_REVISION,
        local_files_only=True,
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


def generate_with_meta(prompt, answer_language="English"):
    """
    RAG 답변 생성 + 추론 메타데이터 반환
    """
    tokenizer, _, pipe = _ensure_pipeline()
    messages = [
        {
            "role": "system",
            "content": (
                "You are a Harry Potter expert. "
                f"Answer concisely in {answer_language} using only the provided context."
            ),
        },
        {"role": "user", "content": prompt}
    ]

    input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    input_ids = tokenizer.encode(input_text, return_tensors="pt")
    input_token_count = input_ids.shape[1]

    print("\n" + "-"*60)
    print(f"[DEBUG] Prompt Token Count: {input_token_count}")
    print("[DEBUG] Local Inference in Progress...")
    print("-"*60)

    start_time = time.perf_counter()
    outputs = pipe(
        input_text,
        max_new_tokens=300,
        do_sample=True,
        temperature=0.3,
        top_p=0.9
    )
    end_time = time.perf_counter()
    duration = end_time - start_time

    full_output = outputs[0]["generated_text"]
    response = full_output.split("[|assistant|]")[-1].strip()
    output_token_count = len(tokenizer.encode(response))
    throughput = 0.0 if duration <= 0 else output_token_count / duration

    print(f"[DEBUG] Latency: {duration:.2f}s")
    print(f"[DEBUG] Throughput: {throughput:.2f} tokens/s")
    print(f"[DEBUG] Response Token Count: {output_token_count}")
    print("-"*60 + "\n")

    return {
        "response": response,
        "full_generated_text": full_output,
        "prompt_token_count": int(input_token_count),
        "response_token_count": int(output_token_count),
        "latency_sec": float(duration),
        "throughput_tokens_per_sec": float(throughput),
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
    }

def rag_answer(prompt, answer_language="English"):
    """
    RAG 답변 생성 및 추론 성능 지표 출력
    """
    result = generate_with_meta(prompt, answer_language=answer_language)
    return result["response"]
