# Open Questions

Running log of unresolved questions across all study sections.

---

## Section 01 — Product Overview & Positioning

- How does the LangGraph-compatible API surface (`/api/langgraph/*`) map internally? Is it thin nginx routing, or does the Gateway implement the LangGraph HTTP protocol itself?
- What exactly does the provisioner container do? The README implies Kubernetes sandbox pod scheduling — what RPC protocol connects Gateway → provisioner?
- v1 Deep Research architecture: what was its LangGraph graph structure? Knowing the baseline clarifies what v2 replaced.
- `DEER_FLOW_PROJECT_ROOT` vs `DEER_FLOW_HOME` — why two separate env vars? One for config, one for runtime state?
- How does LangGraph's concept of "assistant" (`assistant_id: lead_agent`) map to DeerFlow's internal agent model?
