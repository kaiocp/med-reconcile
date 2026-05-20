# Reconciliation Pipeline

```mermaid
flowchart TD
    IN([POST /api/v1/reconciliation])
    IN --> VAL["Pydantic Request Validation · deterministic"]
    VAL -->|invalid payload| E422[/"422 · HARD FAIL"/]
    VAL -->|valid| F1

    subgraph FHIR Adapter
        F1["Fetch Patient · deterministic"]
        F1 -->|not found| E404[/"404 · HARD FAIL"/]
        F1 -->|unavailable| E503[/"503 · HARD FAIL"/]
        F1 -->|ok| F2["Get Pregnancy Status · deterministic"]
        F2 -->|invalid status| E503
        F2 -->|ok| F3["Fetch Active Medications · deterministic"]
        F3 -->|unavailable| E503
    end

    F3 -->|ok| A1

    subgraph Allergy Adapter
        A1["Fetch Allergies · deterministic\nsafe wrapper — never raises"]
        A1 -->|any failure| ADEG(["allergy_data_status = unavailable · DEGRADED"])
        A1 -->|ok| AOKP(["allergies available"])
    end

    ADEG --> D1
    AOKP --> D1

    subgraph DrugBank Adapter
        D1["Check Drug–Drug Interactions · deterministic"]
        D1 --> D2["Map Severity · deterministic"]
        D2 --> D3["Pregnancy Contraindication Overlay · deterministic"]
    end

    D3 --> AC["Check Allergy Conflicts · deterministic"]
    AC --> L1

    subgraph LLM Adapter
        L1["Generate Clinical Summary · probabilistic"]
        L1 -->|any failure| LDEG(["summary_status = unavailable · DEGRADED"])
        L1 -->|ok| L2["Validate LLM Output · deterministic"]
        L2 --> L3["Build Audit Info · deterministic"]
    end

    LDEG --> OUT
    L3 --> OUT

    OUT([200 OK · ReconciliationResponse])
```

**HARD FAIL** — stops immediately, returns an error response: patient not found (404), FHIR unavailable (503), invalid request (422).

**DEGRADED** — returns 200 with explicit status flags: `allergy_data_status = "unavailable"` if the allergy source is unreachable; `summary_status = "unavailable"` if the LLM call fails. Deterministic drug-drug and allergy data are always present in the response.
