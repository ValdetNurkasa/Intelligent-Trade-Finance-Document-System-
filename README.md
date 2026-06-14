# ITFDS - Intelligent Trade Finance Document System

Multi-agent AI pipeline for automated documentary credit examination and settlement routing.

## Setup

pip install -r requirements.txt
cp .env.example .env

## Run

python run.py --bundle trade_bundles/bundle_001

## Team and Ownership

| Person | Role | Agents |
|--------|------|--------|
| P1 | Platform, Schemas, Orchestration | Agent A, Agent H shell |
| P2 | Extraction and Matching | Agent B, Agent D |
| P3 | Compliance, Sanctions, Decisions | Agent C, Agent E, Agent H logic |

## Branch Model

| Branch | Purpose |
|--------|---------|
| main | Protected - demo-ready only |
| develop | Integration - everyone merges here to test |
| p1/... | Person 1 feature branches |
| p2/... | Person 2 feature branches |
| p3/... | Person 3 feature branches |

## Output Artifacts

| File | Agent | Description |
|------|-------|-------------|
| context_packet.json | A | L/C terms, parties, evidence index |
| extracted_docs.json | B | All fields and confidence scores |
| ucp_result.json | C | UCP 600 compliance findings |
| match_result.json | D | Cross-document consistency check |
| sanctions_screen.json | E | Sanctions screening results |
| discrepancies.md | H | Discrepancy list and severity |
| swift_draft.txt | H | MT700/MT752 message draft |
| audit_log.md | H | Step-by-step trace of every decision |
| metrics.json | H | Throughput, accuracy, discrepancy rates |
