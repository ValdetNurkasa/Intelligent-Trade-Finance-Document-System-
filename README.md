# ITFDS - Intelligent Trade Finance Document System

A multi-agent AI pipeline that automates documentary credit examination and settlement routing in trade finance operations.

## What it does

ITFDS takes a trade bundle (Letter of Credit + supporting documents) and runs it through a 6-agent pipeline that classifies documents, extracts fields, checks UCP 600 compliance, matches cross-document data, screens for sanctions, and produces a final honour/refuse decision — all in under a second.

## Setup

Install dependencies:

    pip install -r requirements.txt

Copy the environment file and add your API key if using LLM extraction:

    cp .env.example .env

## Run

Run the pipeline against a trade bundle:

    python run.py --bundle tests/bundles/scenario_01

Run the web interface:

    python -m streamlit run app/ui/streamlit_app.py

Run all 9 test scenarios:

    make test

Run the demo scenario:

    make demo

## Pipeline

The pipeline runs six agents in sequence:

    A -> B -> C -> D -> E -> H

| Agent | Name | Owns |
|-------|------|------|
| A | Document Intake and Context | Loads manifest, classifies documents, builds context packet, generates evidence index, detects risk flags |
| B | Field Extraction | Extracts structured fields from PDFs with confidence scoring and bounding boxes |
| C | UCP 600 Compliance | Validates against UCP 600 rules: expiry, presentation period, partial shipments, transhipment |
| D | Cross-Document Matching | Checks consistency across all documents using fuzzy matching and amount tolerance |
| E | Sanctions Screening | Screens all parties and vessels against OFAC, EU, and UN lists |
| H | Orchestration and Triage | Merges findings, applies decision rules, generates SWIFT draft and discrepancy report |

## Output Artifacts

Every run produces these files in runs/<run_id>/:

| File | Description |
|------|-------------|
| context_packet.json | L/C terms, parties, evidence index, risk flags |
| extracted_docs.json | All extracted fields with confidence scores and bounding boxes |
| extracted_docs.csv | Same data in CSV format |
| ucp_result.json | UCP 600 compliance findings |
| match_result.json | Cross-document consistency check results |
| sanctions_screen.json | Sanctions screening results and hit evidence |
| discrepancies.md | Discrepancy list with severity ratings |
| final_decision.json | Final decision with findings summary |
| posting_payload.json | Structured payload for downstream systems |
| swift_draft.txt | MT700 or MT752 message draft |
| audit_log.md | Step-by-step trace of every agent decision |
| run_metadata.json | Run timestamps, bundle info, event trace |
| metrics.json | Throughput, extraction accuracy, discrepancy rates |
| reports/run_report.md | Human-readable summary report |

## Test Scenarios

Nine scenarios covering the full range of trade finance outcomes:

| Scenario | Description | Expected |
|----------|-------------|----------|
| scenario_01 | Clean presentation, all documents compliant | HONOUR |
| scenario_02 | Bill of lading date after L/C expiry | REFUSE |
| scenario_03 | Invoice amount within tolerance | HONOUR |
| scenario_04 | Partial shipment prohibited | REFUSE |
| scenario_05 | Beneficiary name variation | HONOUR |
| scenario_06 | Sanctions hit on vessel flag state | REFUSE |
| scenario_07 | Late presentation — 21-day rule breach | REFUSE |
| scenario_08 | Low OCR confidence on invoice amount | HONOUR |
| scenario_09 | Clean sight L/C within validity | HONOUR |

## Architecture

### Branch Model

| Branch | Purpose |
|--------|---------|
| main | Protected — demo-ready only, merged at end of each week |
| develop | Integration — everyone merges here to test |
| p1-* | Person 1 feature branches |
| p2-* | Person 2 feature branches |
| p3-* | Person 3 feature branches |

### Team Ownership

| Person | Role | Agents | Key Files |
|--------|------|--------|-----------|
| P1 | Platform, Schemas, Orchestration | A, H shell | agent_a_intake.py, pipeline.py, state.py, schemas/, audit/, utils/, ui/, reports/ |
| P2 | Extraction and Matching | B, D | agent_b_extraction.py, agent_d_matching.py, parsing/, llm/extractor.py |
| P3 | Compliance, Sanctions, Decisions | C, E, H logic | agent_c_ucp.py, agent_e_sanctions.py, rules/, llm/narrator.py |

### Design Decisions

The LLM is off by default (USE_LLM=false). All compliance verdicts, sanctions hits, and the final honour/refuse decision are 100% rule-based and deterministic. The LLM is used only for field extraction in Agent B when enabled.

Same input always produces the same output. JSON keys are sorted, IDs are deterministic hashes, and no wall-clock timestamps appear inside decision logic.

Every finding carries an evidence pointer back to the exact document, page, and field it came from.

## Configuration

Edit config/policy_pack.yaml to change thresholds without touching code:

    tolerance_percent: 5.0
    presentation_period_days: 21
    name_match_threshold: 0.85
    sanctions_freeze_threshold: 1.0
    country_risk_escalation_tier: 3

Regional overrides are in config/regional/.
