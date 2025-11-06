## Agentic RAG Work Guide

A practical, step-by-step playbook to build an agentic RAG that ingests client chats (text and images), reasons with context, proposes empathetic business responses, handles conflict or potential conflict, and iterates via tool-using substeps. Optimized for LangChain 1.0+ (LCEL), Ollama, ChromaDB, Streamlit UI, and optional OCR.

### Core Outcomes
- Context-grounded, business-friendly answers with zero tech jargon
- Multimodal input: pasted images (OCR) + text
- Memory/threading: per conversation state with cache
- Agentic loop: clarify → retrieve → synthesize → verify → propose → (optionally) act/log
- Conflict handling: detect sentiment/risk; escalate or de-escalate
- Regeneration: bypass cache for new variations

---

## 1) Architecture Overview
- UI: Streamlit chat with unified input (paste images, type text)
- OCR: EasyOCR (GPU first, CPU fallback) → text extraction
- Chunking: RecursiveCharacterTextSplitter (size≈1500, overlap≈150)
- Embeddings: Ollama `nomic-embed-text` → Chroma vector store
- LLM: Ollama `deepseek-r1:8b` (GPU prioritized; CPU fallback)
- Retrieval: top_k≈2 for fast, focused context
- Memory: `ConversationManager` (threads + cache by similarity)
- Agent layer: LCEL graph with tools
  - Tools: retriever, sentiment/conflict classifier, policy/risk checker, response composer, follow-up Q generator

---

## 2) Agent Workflows

### A. Client Message Intake
1. Accept text or pasted screenshot (data URI → PIL → OCR → text)
2. Normalize (trim, collapse whitespace)
3. Detect multiple questions → structure as enumerated list
4. Build “enhanced question” with short client context (thread memory)

### B. Agentic Reasoning Loop (per turn)
1. Classify intent + sentiment + conflict risk (low/med/high)
2. Retrieve top_k chunks with embeddings
3. Draft answer options (2+) with different tones
4. Verify grounding (cite internally; do not show citations to user)
5. Hallucination guard: if evidence weak → ask clarifying follow-up
6. Conflict handling: apply de-escalation template if risk ≥ medium
7. Output suggestions; user may “Use This” or “Regenerate” (bypass cache)
8. Cache selected answer for similar future queries

### C. Conflict/Potential-Conflict Handling
- Detect markers: negative sentiment, urgency, refund/complaint, confusion, repeated dissatisfaction
- Strategy:
  - Acknowledge feelings + summarize issue
  - State what you can check/do now
  - Give one concrete next step + timeline
  - Offer escalation path (named role/team) when needed

---

## 3) Prompts (Business-Tuned)

### A. Answer Synthesis (grounded; business tone)
```text
Role: You are a caring, professional assistant for sales/marketing/office teams.

Context (from documents):
{context}

Conversation so far:
{conversation_context}

Client inquiry:
{question}

Guidelines:
- Use clear, friendly business language; avoid technical jargon
- Be concise but complete
- Use ONLY information grounded in the context; if missing, say you don’t have it
- If multiple questions are present, answer all, organized clearly
- If conflict risk is present, acknowledge feelings, propose a concrete next step, and set expectations kindly
Output 2–3 different response options, each ready to send.
```

### B. Conflict De‑Escalation Insert (conditional)
```text
If sentiment=negative or risk>=medium, prepend:
"I’m really sorry this has been frustrating. I appreciate you bringing it up so we can make it right."
Then: brief summary of their point + 1 helpful next step + timeline.
```

### C. Follow‑Up Question (anti‑hallucination)
```text
If context insufficient, ask exactly one clarifying question that helps you answer precisely, without overwhelming the client.
```

---

## 4) LCEL Graph (Concept)

```python
# Pseudocode (LCEL-style composition)
from langchain_core.runnables import RunnableLambda, RunnableParallel

detect_conflict = RunnableLambda(classify_conflict_sentiment)
retrieve = retriever.as_runnable()
compose_prompt = RunnableLambda(build_prompt)
llm_call = llm
parse_suggestions = RunnableLambda(parse_multi_responses)
verify_grounding = RunnableLambda(guardrails_verify)

agent = (
    RunnableParallel({
        "conflict": detect_conflict,
        "docs": retrieve,
        "context": RunnableLambda(lambda x: format_docs(x["docs"]))
    })
    | compose_prompt
    | llm_call
    | parse_suggestions
    | verify_grounding
)
```

---

## 5) Tools (Minimum Set)
- retriever(docs): Chroma top_k=2
- classify_conflict_sentiment(text): rule-based + LLM fallback
- guardrails_verify(answer, context): ensure claims appear in context
- follow_up_generator(text, missing_bits): single clarifying question

---

## 6) Data & Memory
- Threads: `thread_id → [messages]`
- Cache: Jaccard/semantic similarity → answer + sources + timestamp
- Persistence: `cache/` directory json; vector store `./vectorstore/chroma_db`

---

## 7) Multimodal (Images → OCR)
- Accept data URI or bytes → PIL → EasyOCR
- GPU-first (torch.cuda.is_available), CPU fallback with diagnostics
- Extract name/inquiry; detect multiple questions; structure into list

---

## 8) Performance Defaults
- LLM: `num_gpu=-1`, `num_batch=1024`, `num_ctx=8192`, `temperature=0.6`, `max_tokens=400`
- Embeddings: `nomic-embed-text`, batch=200
- Retrieval: `top_k=2`
- CPU parallel PDF processing: `max_workers=4`

---

## 9) UI Behaviors
- Show client name (if available)
- Display structured multi-question view
- Buttons: “Use This”, “Regenerate”, “New Thread”
- Expander: full extracted text from OCR
- Error copy: friendly, actionable

---

## 10) Conflict Templates (Use as blocks)

### A. Acknowledge + Next Step
```text
I’m really sorry this has been frustrating. I appreciate you sharing the details.
Here’s what I can do right now: [specific step]. You’ll hear back by [timeframe].
```

### B. De‑Escalation for Misunderstanding
```text
Thanks for flagging this—totally fair question. Based on our policy, here’s how it works: [brief].
Would [option A] or [option B] help you best right now?
```

### C. Escalation Offer
```text
If you’d like, I can escalate this to our [team/lead]. They typically respond within [SLA].
```

---

## 11) Regeneration Policy
- Always allow “Regenerate” (bypass cache) for variety
- Keep first choice cached unless user opts to overwrite

---

## 12) Guardrails & Hallucination Controls
- Always verify key claims exist in retrieved context
- If evidence is weak → ask one clarifying question
- Never mention file paths, code, or internal metadata

---

## 13) Testing Checklist
- [ ] Paste screenshot with multiple numbered questions → itemized + answers
- [ ] Similar question → cached; “Regenerate” yields new variations
- [ ] Negative/tense client text → de‑escalation openers present
- [ ] No docs matching → graceful “don’t have that info” + follow‑up
- [ ] GPU present → OCR logs GPU in use; otherwise CPU fallback
- [ ] Response time acceptable (<3–5s on short queries with cache)

---

## 14) Rollout & Ops
- Logging: store thread_id, timestamps, chosen response, cache hits
- Metrics: response latency, cache hit rate, CSAT proxy (👍 / 👎)
- Content updates: re-embed and persist vector store on new docs
- Backups: `cache/` and `vectorstore/` folders

---

## 15) Quick Start Task List
1. Enable OCR (optional) and verify GPU (PyTorch with CUDA)
2. Prepare documents → chunk → embed → persist to Chroma
3. Wire LCEL agent graph with tools above
4. Implement conflict classifier and templates
5. Add regenerate/caching logic in UI
6. Test with real client chats and screenshots
7. Monitor logs; tune prompts and thresholds

---

## 16) Example “Agent Instruction” (system prompt)
```text
You are a warm, professional assistant serving sales, marketing, and office teams.
Your priorities: accuracy, empathy, clarity, and business impact.
Use only the provided document context. If unknown, say so and ask a short follow‑up.
Detect conflict risk; if present, lead with empathy and propose a concrete next step.
Produce 2+ response options with slightly different tones.
```

---

## 17) Notes for 4GB GPUs (GTX 1050 Ti)
- Keep context and batch sizes at defaults above; increase only if stable
- If PyTorch says CUDA not available, install CUDA build of PyTorch (see `fix_gpu_cuda.md`)

---

## 18) Where to Extend Next
- Add tool for CRM write-back (log chosen response)
- Add per-account memory summaries (last N facts)
- Add safety filter for PI/PHI in client text


