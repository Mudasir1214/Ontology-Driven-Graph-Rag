"""
relevance_check.py  –  LLM-based query relevance classifier.

Before any retrieval runs, this module asks the LLM a single yes/no question:
"Is this query related to BSM engineering standards?"

If yes  → retrieval proceeds normally.
If no   → retrieval is skipped, LLM answers conversationally.

This replaces the fragile keyword/stop-word approach which could never
enumerate all possible off-topic questions ("what is the purpose of building
a RAG system?", "how does Neo4j work?", "what is Python?" etc.)

The classifier call is fast (~0.3s) because:
  - max_tokens is limited to 1 token ("Y" or "N")
  - No streaming
  - Result is cached per query within a session
"""
from __future__ import annotations
from config import get_llm_client

_CLASSIFIER_SYSTEM = """You are a query classifier for a Building Services Maintenance (BSM) \
engineering knowledge system.

The system contains technical standards and rules about:
- Mechanical systems (pipes, pumps, vibration isolators, HVAC, ductwork)
- Electrical systems (cables, wiring, HV equipment, trunking, cable trays)
- Fire protection systems (sprinklers, fire cables, detection)
- Plumbing and drainage (pipe materials, coatings, fittings, joints)
- Building services installation standards and codes of practice

Reply with exactly one character:
Y  — if the query is asking about any of the above technical topics
N  — if the query is a greeting, general conversation, meta-question about
     the system itself, or unrelated to BSM engineering

Examples:
"Hi" → N
"How are you?" → N
"What is RAG?" → N
"What is the purpose of building a RAG system?" → N
"How does Neo4j work?" → N
"What are the spring mount clearance requirements?" → Y
"copper pipe jointing" → Y
"ductile iron coating standards" → Y
"minimum conduit diameter" → Y
"cable loop before vibrating equipment" → Y
"what is the HV label size?" → Y
"""


def is_bsm_relevant(query: str) -> bool:
    """
    Returns True if the query is related to BSM engineering topics.
    Uses a single fast LLM call with max_tokens=1.
    Falls back to True on any error so retrieval always runs if classifier fails.
    """
    try:
        client   = get_llm_client()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system",  "content": _CLASSIFIER_SYSTEM},
                {"role": "user",    "content": query},
            ],
            max_tokens=1,
            stream=False,
            temperature=0.0,   # deterministic — always Y or N
        )
        answer = response.choices[0].message.content.strip().upper()
        return answer == "Y"
    except Exception:
        # If classifier fails for any reason, allow retrieval to proceed
        return True