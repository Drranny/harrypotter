def build_prompt(contexts, query, answer_language="English"):
    """
    EXAONE 3.5 맞춤형 RAG 프롬프트 생성
    모델의 특수 태그([|system|], [|user|], [|assistant|]) 구조를 활용
    """
    # 1. 컨텍스트를 하나로 합침 (가독성을 위해 번호 부여)
    context_str = ""
    for i, ctx in enumerate(contexts[:3], 1):
        context_str += f"[{i}] {ctx}\n"
    
    # 2. EXAONE의 Instruction Following 성능을 높이는 프롬프트 구성
    # 시스템 역할과 참고 자료를 명확히 구분해줍니다.
    system_msg = (
        "You are a truthful and accurate AI assistant specialized in Harry Potter. "
        "Your task is to answer the user's question **ONLY based on the provided Information** below.\n\n"
        "### Strict Rules (You MUST follow):\n"
        "1. **No Outside Knowledge:** Do NOT use your pre-trained knowledge. Only use the text in 'Information'.\n"
        "2. **No Hallucination:** If the answer is not in the Information, strictly say: 'The provided documents do not contain the answer.' Do not make up an answer.\n"
        "3. **Be Specific:** For specific entities (e.g., 'Ocean Ravenclaw'), check if the EXACT name exists. If not, state that it is not mentioned.\n"
        f"4. **Language:** Answer in {answer_language}."
    )
    
    # EXAONE 전용 포맷팅
    prompt = f"""[|system|]{system_msg}

Information:
{context_str}
[|user|]{query}
[|assistant|]"""
    
    return prompt
