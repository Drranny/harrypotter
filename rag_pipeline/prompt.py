def build_prompt(contexts, query, answer_language="English", query_type=""):
    """
    Build a plain-text user prompt for the chat template.

    The tokenizer chat template already adds the model-specific role markers,
    so this function should not inject EXAONE tags itself.
    """
    context_lines = []
    for i, ctx in enumerate(contexts, 1):
        context_lines.append(f"[{i}] {ctx}")
    context_str = "\n".join(context_lines)

    query_type = (query_type or "").strip().upper()
    if query_type == "FACT":
        answer_style = (
            "Answer with the exact entity or short phrase only, not a full explanation. "
            "Prefer the full proper name when the context supports it. "
            "Do not add hedging or outside knowledge."
        )
    else:
        answer_style = (
            "Answer in 1-2 concise sentences using only the provided information. "
            "Include the key entities and the core causal relation when available."
        )

    return (
        "You are a truthful and accurate AI assistant specialized in Harry Potter.\n"
        "Answer the question using ONLY the information below.\n\n"
        "Rules:\n"
        "1. Do not use outside knowledge.\n"
        "2. If the answer is not supported by the information, reply exactly: "
        "'The provided documents do not contain the answer.'\n"
        "3. Use the exact wording from the information when possible.\n"
        f"4. Answer in {answer_language}.\n"
        f"5. {answer_style}\n\n"
        f"Information:\n{context_str}\n\n"
        f"Question: {query}"
    )
