# System Architecture Overview: Integrated Multi-Agent & CRM Ecosystem

This document provides a production-grade blueprint for an integrated, multi-tenant agentic ecosystem. It synthesizes the orchestration, gateway routing, web-research, visual prototyping, and customer data management paradigms found across **Dify**, **OmniRoute**, **Perplexica**, **Langflow**, and **Twenty CRM**.

---

## 1. System Topology & Core Subsystems

The ecosystem is partitioned into five distinct logical pillars, with strict decoupled operational boundaries:

```
[Client App / Frontend]
          │ (Stateful WS / Streamed HTTP)
          ▼
[Langflow Visual Graph Engine] ─── (DAG JSON Export) ───► [Dify Orchestration Engine]
                                                                  │
         ┌──────────────────────────────┬─────────────────────────┴────────────────────────┐
         ▼                              ▼                                                    ▼
[Twenty CRM Data Core]        [Perplexica Web-Research]                             [OmniRoute AI Gateway]
  (Relational PostgreSQL)       (SearXNG Multi-Scraper)                               (Dynamic Provider Layer)
```

*   **Orchestration & Workflow Runtime (Dify-inspired):** Coordinates multi-tenant agent execution, system prompt template rendering, session context matching, and asynchronous task steps via workers.
*   **Resilient AI Gateway & Proxy (OmniRoute-inspired):** Aggregates connection channels across upstream AI providers. Implements advanced prompt compression, circuit breakers, and programmatic failovers.
*   **Deep Web-Research Engine (Perplexica-inspired):** Coordinates automated web search agents, querying localized indices and parsing HTML structures down into clean semantic fragments to ground models.
*   **Visual Prototyping Engine (Langflow-inspired):** A node-based designer that generates Directed Acyclic Graph (DAG) state configurations, verified in isolation prior to system staging.
*   **Operational CRM Core (Twenty CRM-inspired):** Acts as the single point of truth for customer entity models (leads, accounts, pipelines), exposing database state modifications via event listeners.

---

## 2. Global Data Flow Architecture

### A. Ingress & Knowledge Augmentation
When an action triggers from a frontend client, the session payload hits the Orchestration Engine. The engine performs a dual-path hydration pass: it calls the CRM API over high-frequency paths to extract client status variables, while concurrently passing structural terms to the Web-Research Engine. The Research Engine polls search scrapers, cleans incoming data matrices, and passes a compressed summary back to the orchestrator within millisecond limits.

### B. Gateway Optimization & Model Egress
The fully aggregated prompt payload is packed into an OpenAI-compatible interface format. Before exiting the network, it hits the AI Gateway Proxy where token optimization scripts run to strip redundant syntax. The gateway analyzes real-time endpoint latency and account usage limits, choosing the optimal pipeline provider. The streaming data returned from the LLM bypasses local buffers, providing instantaneous chunk updates to the consumer UI.

---

## 3. Unified API Flow Sequence

The chronological sequence below outlines a standard event lifecycle: an incoming user query grounds itself via web discovery, executes through the optimization proxy, updates core company records, and streams the validated results back to the user.

```
Client App       Orchestration      Web-Research      AI Gateway       Core Data Engine
   │                   │                 │                │                    │
   │─── User Query ───>│                 │                │                    │
   │    (HTTP/WS)      │── Search Query ─>│                │                    │
   │                   │   (Axios/REST)  │                │                    │
   │                   │<── Clean Context│                │                    │
   │                   │                 │                │                    │
   │                   │────── OpenAI-Compatible Chat Payload ───────────────>│
   │                   │       (Applies RTK/Caveman + Route Selection)        │
   │                   │<───── Streamed SSE Tokens (Chunk-by-Chunk) ──────────│
   │                   │                 │                │                    │
   │                   │── Write Activity Log / Lead Status ──────────────────>│
   │                   │   (GraphQL Mutation / Webhook Trigger)                │
   │<── Streamed SSE ──│                 │                │                    │
```

---

## 4. Multi-Container Docker Architecture

The platform relies on container isolation blocks, managed via an explicit network overlay configuration to eliminate external attack surfaces.

| Container Identity | Runtime Engine | Port Mapping | Primary Storage Dependencies |
| :--- | :--- | :--- | :--- |
| `orchestrator-core` | Python / FastAPI | `5001:5001` | PostgreSQL (System Configurations), Redis (Shared Memory Cache) |
| `orchestrator-worker` | Python / Celery | Internal | Redis (Task Management Queue), MinIO (Object Workspace storage) |
| `visual-designer` | Python / Langflow | `7860:7860` | PGVector (Design state backups and modular flow storage) |
| `ai-gateway-proxy` | Node.js / TypeScript | `20128:20128` | SQLite (Localized token rate tracker & state cache) |
| `research-agent` | Node.js / Express | `3000:3000` | Redis (Scraping task cache) + SearXNG Sidecar Instance |
| `core-crm-api` | TypeScript / NestJS | `4000:4000` | PostgreSQL (Core Customer Accounts, Structural Profiles) |
| `core-crm-worker` | Node.js / BullMQ | Internal | Redis (Transactional state broadcast queue) |

---

## 5. Service Communication Protocols

*   **Asynchronous State Brokering (Redis / BullMQ):** Inter-service mutations use non-blocking message broker architectures. Database record edits emit broadcast events, notifying listening agent workers to execute corresponding tasks.
*   **High-Frequency Internal Syncs (HTTP/2 & SSE):** Core communication links rely on standardized REST paradigms. Chunk transfers use Server-Sent Events (SSE) to preserve continuous stream properties across systems.
*   **Data Query Planes:** Relational configurations rely on high-performance GraphQL queries over structural data fields, while application sessions leverage specialized in-memory key-value maps.

---

## 6. Comprehensive Bot Lifecycle Management

Autonomous worker sessions step linearly through six lifecycle execution checkpoints:

1. **Bootstrap Phase:** Workers fetch targeted blueprint maps. Structural definitions, prompt variables, and specific third-party plugin paths load directly into regional operational memories.
2. **State Initialization Phase:** The system verifies active session parameters, reads contextual interaction logs, updates user data tokens from the CRM, and secures active worker tracking paths.
3. **Interception & Compression Phase:** Raw inputs are checked for lexical patterns. Text arrays pass through compression routines to reduce overhead, and system models map alternate failover nodes.
4. **Execution Stream Phase:** Prompts route through the proxy layer to active server pools. Token streams pass back through live validation monitors to ensure safe output bounds.
5. **Callback Synchronization Phase:** Upon stream closure, asynchronously deferred workers index logs, write session outputs back to customer profiles, and commit updated API cost sheets.
6. **Teardown Phase:** Volatile runtime structures are scrubbed, transient application memory frames detach, and execution engines clear worker paths for incoming request flows.

---

## 7. Integrated System Extensibility Points

### Model Context Protocol (MCP) Boundary
The system connects third-party utilities directly at the proxy layer via standardized MCP contracts. Upstream LLM setups access internal tools, host execution setups, and custom databases securely without making intrusive configuration changes within core application servers.

### Agent-to-Agent (A2A) Interface
Advanced agent interactions are facilitated via an ultra-low latency JSON-RPC system. Complex pipelines can assign granular sub-routines to specialized workers via a central router interface, isolating operational contexts while preserving global task execution lines.

### Transactional Data Webhooks
The database management plane contains automated entity tracking systems. When records update, webhooks dispatch payload alerts across the cluster. This allows background workflows to immediately trigger lead validation scripts or modify localized vector knowledge pools.
