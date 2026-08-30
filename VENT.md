# VENT

Feedback log. Repeated/systemic workflow friction that should become future automation, docs, or workflow fixes.

## 26-08-30 15:29 — bash tool empty results

bash tool returned "No result provided" for ~8 consecutive calls (including trivial `echo ok`), then recovered on its own. Workaround was repeating the call or switching to process/ffgrep/read tools, which kept working. If this recurs, treat it as transient harness flakiness and route around it instead of retry-looping the same tool.
