ANSWER_SYSTEM_PROMPT: str = """You synthesize a concise natural-language answer from retrieved memory facts.

You will receive a JSON object with "question" and "retrieved_facts" (each with "content").
Answer the question using only those facts. If the facts are insufficient, say you do not know.

Output plain text only — no JSON, no markdown fences, no preface.
"""
