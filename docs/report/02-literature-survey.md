# 02 — Literature survey

Feeds **Chapter 2 (Literature Survey)** of the report. Every work below was checked against the
real paper or its official page. Do not add works that were not verified.

---

## 2.1 How to structure this chapter

Organise the survey in **four themes**, then state the gap. This order builds the argument:

1. **Foundations of grounded generation** — why retrieval matters (§2.2)
2. **Agentic reasoning and multi-agent orchestration** — how agents use tools and cooperate (§2.3)
3. **LLM agents in software engineering** — agents acting on engineering artefacts (§2.4)
4. **LLM-based root cause analysis and AIOps** — the direct domain (§2.5)
5. **Benchmarks and the honest state of the art** — what current systems actually achieve (§2.6)
6. **Research gap** — what nobody has done (§2.7)

---

## 2.2 Foundations: retrieval-augmented generation

**[1] Vaswani et al., NeurIPS 2017 — "Attention is all you need."**
The Transformer architecture; the basis of every model used in this work. Cite once, for lineage.

**[2] Lewis et al., NeurIPS 2020 — "Retrieval-augmented generation for knowledge-intensive NLP tasks."**
Combines a parametric model with a non-parametric retrieval index, so answers are grounded in
retrieved documents rather than in model weights alone.
*Relevance:* the Engineering Memory Layer in this project is an application of RAG to a team's own
runbooks and postmortems.
*Limitation for our problem:* RAG retrieves and generates. It does not act, does not use tools and
does not investigate a live system.

**[3] Gao et al., arXiv:2312.10997, 2023 — "Retrieval-augmented generation for large language models: a survey."**
A survey of RAG variants: naive, advanced and modular pipelines, chunking strategies, hybrid and
re-ranked retrieval.
*Relevance:* justifies our hybrid retrieval (dense embeddings combined with BM25 and fused by
reciprocal rank fusion) over naive single-vector search.

---

## 2.3 Agentic reasoning and multi-agent orchestration

**[4] Yao et al., ICLR 2023 — "ReAct: Synergizing reasoning and acting in language models."**
Interleaves reasoning traces with tool actions, so that a model can look something up instead of
guessing.
*Relevance:* each specialist desk in our system runs a budgeted ReAct loop.
*Limitation:* single agent, single task, unbounded loop length.

**[5] Wu et al., COLM 2024 — "AutoGen: Enabling next-gen LLM applications via multi-agent conversation."**
A framework for building applications from conversable agents that coordinate through dialogue.
*Relevance:* established that specialised agents can cooperate.
*Limitation:* coordination happens through free-form conversation. Nothing bounds the number of
exchanges and nothing forces an agent to prove a claim, so cost grows and accuracy is unverified.

**[6] LangChain AI — "LangGraph: stateful, multi-actor applications with LLMs," 2024.**
Graph-based orchestration with typed state, parallel fan-out (`Send`), reducers that merge concurrent
writes, durable checkpoints and interrupts.
*Relevance:* the implementation substrate for our shared investigation state and the human approval
pause.

---

## 2.4 LLM agents in software engineering

**[7] Yang et al., NeurIPS 2024 — "SWE-agent: Agent-computer interfaces enable automated software engineering."**
Shows that a purpose-built agent-computer interface, rather than a bigger model, is what lets agents
navigate repositories and fix issues.
*Relevance:* strong support for our central claim that **the harness, not the model, determines
quality**.
*Limitation:* confined to a repository; no live telemetry, no incident context, no multi-source
correlation.

**[8] Jimenez et al., ICLR 2024 — "SWE-bench: Can language models resolve real-world GitHub issues?"**
A benchmark of real GitHub issues and their patches.
*Relevance:* a model for how our own evaluation should be constructed — real tasks, verifiable outcomes.
*Limitation:* measures code repair, not diagnosis across systems.

---

## 2.5 LLM-based root cause analysis (the direct domain)

**[9] Ahmed et al., ICSE 2023 — "Recommending root-cause and mitigation steps for cloud incidents using large language models."**
Fine-tunes GPT models to propose a root cause and mitigation from the incident title and summary
available at creation time.
*Limitations:* a single prediction from a short text description; no evidence gathering; fine-tuning
is expensive and becomes stale as incident types evolve.

**[10] Chen et al., EuroSys 2024 — "Automatic root cause analysis via large language models for cloud incidents" (RCACopilot).**
The closest prior system. On-call engineers build an *incident handler* per alert type; the handler
collects diagnostic data from multiple sources; an LLM then predicts the root-cause **category** and
writes an explanation. Evaluated on a year of real Microsoft incidents: **Micro-F1 0.766**,
**Macro-F1 0.533**, average overhead **4.205 s**. The collection component has been in production at
Microsoft for over four years.
*Limitations for our problem:* provider-side (it lives inside one company's telemetry); a handler must
be written by hand for every alert type; it classifies into known categories rather than
investigating an arbitrary customer stack; a single reasoning step rather than parallel specialists.

**[11] Roy et al., FSE 2024 (Industry track) — "Exploring LLM-based agents for root cause analysis."**
Compares a ReAct-style agent with retrieval-augmented and chain-of-thought baselines on
out-of-distribution production incidents. Accuracy was comparable across methods (roughly 35–39%),
but factual errors differed sharply: hallucinations were **49%** of incorrect predictions for the
retrieval baseline, **18%** for chain-of-thought, and **6%** for the ReAct agent.
*Why this is the most important citation in the report:* it is empirical evidence that **tool
grounding buys honesty rather than raw accuracy**. Our design makes that grounding structural — the
harness rejects a finding that cites no successful tool call.
*Limitation:* a single agent performing diagnosis only.

**[12] RCAgent, CIKM 2024 — "Cloud root cause analysis by autonomous agents with tool-augmented large language models."**
An autonomous, tool-augmented agent for cloud RCA deployed in an industrial platform, with attention
to privacy and self-consistency.
*Limitation:* single agent, provider-side, one company's internal tooling.

---

## 2.6 Benchmarks and the honest state of the art

**[13] OpenRCA, ICLR 2025 — "Can large language models locate the root cause of software failures?"**
The first public RCA benchmark: **335 failure cases** from three enterprise systems with more than
**68 GB** of telemetry. Even with a purpose-built RCA agent, the best model solved only **11.34%** of
cases; without the agent the figure was lower still.
*Use in the report:* this is the evidence that fully autonomous root-cause analysis is not yet
reliable, which justifies our human-in-the-loop design.

**[14] AIOpsLab, MLSys 2025 — "A holistic framework to evaluate AI agents for enabling autonomous clouds."**
An open framework that deploys microservice applications, injects faults, generates workload and
evaluates agents across detection, localisation, root-cause analysis and mitigation.
*Use in the report:* our planned Experiment 4 harness. The same body of work reports the 52.5-hour
median time-to-mitigate figure used as motivation (AidAI, arXiv:2506.01481, 2025).

**[15] ITBench, ICML 2025 — "Evaluating AI agents across diverse real-world IT automation tasks."**
IBM's benchmark across SRE, compliance and FinOps tasks. Agents built on state-of-the-art models
resolved only **11.4%** of SRE scenarios; a 2026 leaderboard built on 59 Kubernetes SRE tasks still
shows all frontier models **below 50%**.
*Use in the report:* independent confirmation of the same conclusion as OpenRCA.

**[16] Chroma — "The AI-native open-source embedding database," 2024.**
The vector store used by the Engineering Memory Layer.

---

## 2.7 Comparative analysis

Use this table in the report; it is the heart of Chapter 2.

| Work | Multi-source | Parallel specialised agents | Agent-to-agent questions | Customer-side, any stack | Enforced evidence citation | Human approval for writes |
|---|---|---|---|---|---|---|
| Ahmed et al. (ICSE'23) | No | No | No | No | No | n/a |
| RCACopilot (EuroSys'24) | Via handwritten handlers | No | No | No | No | n/a |
| Roy et al. (FSE'24) | Partial | No | No | No | Partial | n/a |
| RCAgent (CIKM'24) | Yes | No | No | No | Partial | Partial |
| SWE-agent (NeurIPS'24) | No | No | No | No | No | No |
| AutoGen (COLM'24) | n/a | Yes (conversational) | Yes (unbounded) | n/a | No | No |
| **EOPS (this work)** | **Yes** | **Yes** | **Yes (budgeted)** | **Yes** | **Yes** | **Yes** |

## 2.8 Research gap

Three gaps follow from the table:

1. **Provider-side versus customer-side.** Every deployed RCA system is built inside one cloud
   provider's own telemetry, with collection logic written per alert type. A small software team
   cannot use any of them on its own mixed stack of GitHub, a managed database, a hosting platform
   and a content system.
2. **Single reasoning step versus coordinated investigation.** Prior systems either predict in one
   shot or run one agent. None assigns independent specialists to different system areas, runs them
   concurrently, and lets them query one another within a budget.
3. **Hoped-for grounding versus enforced grounding.** Roy et al. showed that tool use reduces
   hallucination dramatically, but in existing systems nothing *prevents* an unsupported claim. No
   prior system rejects a finding that cites no successful tool call, or caps confidence in code
   rather than trusting the model's own estimate.

**Statement of the gap for the report:** *No existing system coordinates several specialised agents
over a customer's own heterogeneous engineering tools, sharing a single investigation state in which
every finding must cite the tool call that produced it, while reserving all write actions for human
approval.*

---

## 2.9 Reference list (IEEE style)

```
[1]  A. Vaswani et al., "Attention is all you need," in Proc. NeurIPS, 2017.
[2]  P. Lewis et al., "Retrieval-augmented generation for knowledge-intensive NLP tasks,"
     in Proc. NeurIPS, vol. 33, pp. 9459–9474, 2020.
[3]  Y. Gao et al., "Retrieval-augmented generation for large language models: A survey,"
     arXiv:2312.10997, 2023.
[4]  S. Yao et al., "ReAct: Synergizing reasoning and acting in language models," in Proc. ICLR, 2023.
[5]  Q. Wu et al., "AutoGen: Enabling next-gen LLM applications via multi-agent conversation,"
     in Proc. COLM, 2024.
[6]  LangChain AI, "LangGraph: Building stateful, multi-actor applications with LLMs," 2024.
     [Online]. Available: https://langchain-ai.github.io/langgraph/
[7]  J. Yang et al., "SWE-agent: Agent-computer interfaces enable automated software engineering,"
     in Proc. NeurIPS, vol. 37, pp. 50528–50652, 2024.
[8]  C. E. Jimenez et al., "SWE-bench: Can language models resolve real-world GitHub issues?",
     in Proc. ICLR, 2024.
[9]  T. Ahmed et al., "Recommending root-cause and mitigation steps for cloud incidents using
     large language models," in Proc. ICSE, 2023.
[10] Y. Chen et al., "Automatic root cause analysis via large language models for cloud incidents,"
     in Proc. EuroSys, pp. 674–688, 2024.
[11] D. Roy et al., "Exploring LLM-based agents for root cause analysis," in Proc. FSE
     (Industry Track), 2024.
[12] "RCAgent: Cloud root cause analysis by autonomous agents with tool-augmented large language
     models," in Proc. CIKM, 2024.
[13] "OpenRCA: Can large language models locate the root cause of software failures?",
     in Proc. ICLR, 2025.
[14] "AIOpsLab: A holistic framework to evaluate AI agents for enabling autonomous clouds,"
     in Proc. MLSys, 2025.
[15] "ITBench: Evaluating AI agents across diverse real-world IT automation tasks,"
     in Proc. ICML, 2025.
[16] Chroma, "Chroma: The AI-native open-source embedding database," 2024.
     [Online]. Available: https://docs.trychroma.com/
```

**Note on [12]–[15]:** author initials for these four were not verified against the published
front matter. Either verify them before submission or keep the title-first form shown above.
