# IdentityOS Runtime

Portable AI identity layer — own your AI's soul, not just its prompt.

## Architecture

```
┌──────────────────────────────────────────────────┐
│                   SDK / API Layer                 │
│        (sdk/identity_object.py, FastAPI)          │
├──────────────────────────────────────────────────┤
│              IdentityRuntime (orchestrator)        │
│         (runtime/orchestrator.py — microkernel)   │
│            EventBus — decoupled eventing          │
├────┬─────┬──────┬──────┬──────┬──────┬──────┬────┤
│    │     │      │      │      │      │      │    │
│ ID │ Mem │ Know │ Skill│ Goal │ Eval │ Rel  │ ...│
│    │     │      │      │      │      │      │    │
└────┴─────┴──────┴──────┴──────┴──────┴──────┴────┘
```

### Core Domain Modules (`core/`)

| Module | Description |
|---|---|
| `identity.py` | IdentitySpec (schema, versioning, serialization) |
| `memory.py` | MemoryFragment, MemoryStore, PersistentMemoryStore (SQLite) |
| `cognitive_engine.py` | ContextComposer — assembles LLM context from all modules |
| `evaluation.py` | EvaluationEngine, heuristic memory classification |
| `relationships.py` | Re-exports from `identity_graph/graph.py` |
| `goals.py` | GoalEngine — identity goal tracking |
| `policies.py` | PolicyEngine — input/output guardrails |
| `skills.py` | SkillRegistry — composable skills |
| `knowledge.py` | KnowledgePack — domain expertise |
| `experience.py` | ExperienceStore — session-level experience |
| `timeline.py` | TimelineRegistry — chronological narrative |
| `motivations.py` | MotivationEngine — drive/need simulation |
| `permissions.py` | PermissionManager — access control |
| `snapshot.py` | SnapshotManager — identity state snapshots |
| `health.py` | HealthEngine — system monitoring |

### Identity Graph (`identity_graph/`)

| Module | Description |
|---|---|
| `graph.py` | Directed weighted graph for identity relationships |

### Runtime (`runtime/`)

| Module | Description |
|---|---|
| `orchestrator.py` | IdentityRuntime microkernel — 8-stage pipeline |
| `main.py` | FastAPI service (routes through orchestrator) |
| `event_bus.py` | Pub/sub eventing for decoupled modules |
| `persistence.py` | Storage backends |

*Deprecated modules (re-export shims):* `eval_engine.py`, `memory_engine.py`, `context_builder.py`, `identity_loader.py`

### SDK (`sdk/`)

| Module | Description |
|---|---|
| `identity_object.py` | High-level developer API for creating/managing identities |

## Getting Started

```bash
python3 -m pip install -r runtime/requirements.txt
PYTHONPATH=. python3 -m uvicorn runtime.main:app
```

## Testing

```bash
PYTHONPATH=. python3 -m pytest tests/
```

## Pipeline

The orchestrator processes each interaction through 8 stages:

1. **Resolve** — load identity spec
2. **Input Policy** — gate input content
3. **Compose Context** — assemble identity + memory + skills + goals
4. **Adapter** — invoke LLM (via pluggable adapter)
5. **Output Policy** — gate output content
6. **Evaluate** — score quality, detect memorable content
7. **Store** — persist interaction in memory
8. **Respond** — return result to caller

Events are emitted at every stage for subscribers on the EventBus.
