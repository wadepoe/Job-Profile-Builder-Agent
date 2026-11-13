# Specification: job-profile-builder-agent

> **Guidelines**: Read all applicable guidelines before executing ANY tasks below:
> - [guidelines.md](../guidelines.md) — Universal execution rules
> - [guidelines-agent.md](../guidelines-agent.md) — Universal agent patterns
> - [guidelines-agent-python.md](../guidelines-agent-python.md) — Python implementation details
> - [guidelines-agent-skills.md](../guidelines-agent-skills.md) — Runtime skills patterns
> - [guidelines-agent-mcp.md](../guidelines-agent-mcp.md) — MCP integration patterns

---

## Basic Setup

- [ ] Read `product-requirements-document.md` and `intent.md` before starting any implementation task
- [ ] Bootstrap agent code in `assets/job-profile-builder-agent/` using instructions from the sap-agent-bootstrap reference (use copy commands — do NOT create files manually)
- [ ] Install dependencies, validate the agent starts and responds at `/.well-known/agent.json`

---

## Runtime Skills

The agent requires the following runtime skills to keep the system prompt focused and modular:

- [ ] Create `assets/job-profile-builder-agent/app/skills/profile-generation/SKILL.md` with:
  - YAML frontmatter: `name: profile-generation`, `description: Step-by-step instructions for generating a template-compliant job profile from provided source data`
  - Body: instructions for field extraction from text/documents, gap identification, template section mapping, AI content generation rules, equal-opportunity language guardrails, and section-by-section review loop guidance

- [ ] Create `assets/job-profile-builder-agent/app/skills/batch-processing/SKILL.md` with:
  - YAML frontmatter: `name: batch-processing`, `description: Instructions for processing a batch input file of multiple job roles and generating profiles for all of them`
  - Body: instructions for parsing batch input (CSV/list formats), iterating roles, handling per-role failures without stopping the batch, API rate-limit backoff behaviour, producing a batch summary report with counts of generated / flagged / failed profiles

- [ ] Create `assets/job-profile-builder-agent/app/skills/output-delivery/SKILL.md` with:
  - YAML frontmatter: `name: output-delivery`, `description: Instructions for delivering a completed job profile in the user's chosen output mode`
  - Body: instructions for the three output modes — (1) API write: call the SuccessFactors Generic Objects write tool with the completed profile payload; (2) CSV export: format the profile as a SuccessFactors Job Profile Builder import-compatible CSV and return the file; (3) document draft: format and return a clean structured document for the user

---

## Project-Specific Tasks

### Source Data Intake (R1)

- [ ] Implement `intake_tool` in `assets/job-profile-builder-agent/app/` to handle the following source types:
  - **Text/paste:** accept raw text, extract job profile fields using LLM structured extraction
  - **File upload:** accept Word (.docx) and PDF file paths; parse document content and extract job profile fields
  - **Clone instruction:** accept a job profile name or code string with instruction to clone; retrieve the profile from SuccessFactors via Generic Objects API read tool and use it as the base
  - **Verbal/conversational:** accept a natural-language description of a role; extract available fields and flag missing required ones
- [ ] The tool must return a structured dict of extracted fields with a confidence flag per field (`found` / `inferred` / `missing`)
- [ ] Emit `M1.achieved: source data received and fields identified — source_type={source_type}, fields_found={fields_found}` on success
- [ ] Emit `M1.missed: no job profile fields could be identified from the provided input — input_type={input_type}` if extraction yields zero fields

### Gap Resolution via SuccessFactors (R2)

- [ ] Implement `gap_resolution_tool` in `assets/job-profile-builder-agent/app/` that:
  - Accepts the extracted field dict from `intake_tool`
  - For each `missing` field, queries SuccessFactors via the appropriate MCP tool:
    - Job family / job function / job level / job code → Generic Objects API (`PLTGenericObjects`)
    - Position context → Position Management API (`ECPositionManagement`)
    - Competencies / skills → Skills Management API (`ECSkillsManagement`)
  - Attempts to match missing fields from SuccessFactors data before asking the user
  - Returns an updated field dict with filled gaps; remaining unresolvable fields are flagged for user Q&A
- [ ] In `agent.py` system prompt: instruct the agent to ask one targeted question per unresolved field, never batching multiple questions unless they are tightly related
- [ ] Emit `M2.achieved: all required fields resolved — fields_from_sf={fields_from_sf}, fields_from_user={fields_from_user}` when all required fields are populated
- [ ] Emit `M2.missed: one or more required fields could not be resolved — missing_fields={missing_fields}` if unresolvable fields remain

### Template-Compliant Profile Generation (R3)

- [ ] Implement `generate_profile_tool` in `assets/job-profile-builder-agent/app/` that:
  - Reads the assigned Job Profile Builder template from SuccessFactors (via `PLTGenericObjects` MCP tool) to get all required sections and their content rules
  - Uses the LLM to generate content for each template section, guided by the `profile-generation` runtime skill
  - Annotates each generated field with its source: `sf_lookup` (from SuccessFactors), `doc_extracted` (from source document), or `ai_generated`
  - Applies content guardrails: scans output for discriminatory language patterns (age, gender, race, disability, national origin) before returning; flags any violations to the user
- [ ] In `agent.py` system prompt: instruct the agent to never fabricate job architecture data; always look up template structure before generating; never omit a required template section
- [ ] Emit `M3.achieved: profile draft generated — template_id={template_id}, sections_populated={sections_populated}` on success
- [ ] Emit `M3.missed: profile draft generation failed — template_id={template_id}, reason={reason}` on failure

### Human Review and Approval Loop (R4)

- [ ] Implement a conversational review loop in `agent.py`:
  - Present each template section to the user with its source annotation
  - Allow the user to request a revision of any section by providing new instructions or replacement text
  - Re-generate only the revised section (not the full profile) when a correction is requested
  - Require an explicit "approve" or "confirm" response before proceeding to output delivery
  - Never write to SuccessFactors or generate output without this explicit confirmation
- [ ] Emit `M4.achieved: user approved draft — revisions_made={revisions_made}` when the user confirms
- [ ] Emit `M4.missed: user did not confirm approval — session_status={session_status}` if the session ends without approval

### Output Delivery — Three Modes (R5)

- [ ] Implement `deliver_profile_tool` in `assets/job-profile-builder-agent/app/` using the `output-delivery` runtime skill, supporting:
  - **Mode 1 — API write:** call the SuccessFactors Generic Objects write MCP tool with the completed, approved profile payload; return the created profile ID and a confirmation message; if the API write fails, automatically offer CSV export as fallback without discarding the approved content
  - **Mode 2 — CSV export:** format the approved profile as a SuccessFactors Job Profile Builder import-compatible CSV (one row per section per profile); return the CSV content for download
  - **Mode 3 — Document draft:** return a clean, human-readable formatted document (markdown or plain text) of the complete profile suitable for copy-paste or filing
- [ ] At runtime, the user selects the output mode; if no selection is made, prompt the user to choose before proceeding
- [ ] Emit `M5.achieved: profile delivered — output_mode={output_mode}, profile_id={profile_id}` on success
- [ ] Emit `M5.missed: output delivery failed — output_mode={output_mode}, reason={reason}` on failure

### Job Requisition Linkage (R8 — High-Want)

- [ ] Implement `link_requisition_tool` in `assets/job-profile-builder-agent/app/` that:
  - Accepts a job requisition ID or title from the user
  - Reads the requisition via the Job Requisition MCP tool (`RCMJobRequisition`) to confirm it exists
  - Writes the profile reference to the requisition (if write-supported) or returns the profile ID for manual linking with instructions
- [ ] This tool is optional; only invoke it when the user explicitly requests it after profile delivery

### Batch Processing Mode (R6)

- [ ] Implement `batch_process_tool` in `assets/job-profile-builder-agent/app/` using the `batch-processing` runtime skill:
  - Accept a batch input as a CSV file path or a newline-delimited list of role names/codes
  - For each role: run the full pipeline (gap resolution → generation → output delivery) automatically without pausing for review between roles
  - API rate-limit management: implement exponential backoff retry (start 1 s, max 30 s, max 3 retries) for all SuccessFactors API calls within batch runs
  - Profiles that cannot be completed (missing required fields that cannot be resolved from SuccessFactors) are flagged in the batch summary and skipped — the remaining roles continue processing
  - After all roles are processed, return a batch summary: `total_roles`, `profiles_generated`, `profiles_flagged`, `profiles_failed`
- [ ] In batch mode, default output mode is CSV export unless the user specifies otherwise at the start of the batch run
- [ ] Emit `M6.achieved: batch run completed — total_roles={total_roles}, profiles_generated={profiles_generated}, flagged={flagged}` on completion
- [ ] Emit `M6.missed: batch run did not complete — roles_processed={roles_processed}, reason={reason}` on failure

### Content Guardrails and Prompt Injection Protection (R7)

- [ ] Implement `guardrail_check` utility in `assets/job-profile-builder-agent/app/` that:
  - Scans any generated content string for discriminatory language patterns using a configurable blocklist (age descriptors, gendered terms, protected-class references)
  - Returns `(clean: bool, flagged_phrases: list)` — if `clean=False`, the content is not presented to the user; instead, the agent regenerates the flagged section with an explicit instruction to avoid those phrases
  - Call `guardrail_check` on every section before including it in the draft presented to the user
- [ ] Implement prompt injection detection in `agent.py` using the bootstrap-provided `prompt_injection_detector.py`:
  - All user-supplied text inputs (source data, file content, verbal descriptions) must pass through the detector before being used in LLM prompts
  - If injection is detected, respond with an explanation and request clean input — do not process the injected content
- [ ] In `agent.py` system prompt: instruct the agent that it exclusively assists with SAP SuccessFactors job profile creation; it must refuse any requests unrelated to job profile generation, HR data look-up, or recruiting-related SuccessFactors operations

### Similarity Search Against Existing Profiles (R9 — High-Want)

- [ ] Implement `find_similar_profiles_tool` in `assets/job-profile-builder-agent/app/` that:
  - Accepts a job title or role description string
  - Queries SuccessFactors via the Generic Objects MCP tool to retrieve existing job profiles
  - Returns the top 3 most similar profiles (by title / job family / job level similarity) for the user to optionally select as a starting point
- [ ] In the `intake_tool` flow, after initial field extraction, call `find_similar_profiles_tool` and present the suggestions to the user before proceeding to gap resolution
- [ ] This is optional; if the user declines, proceed directly to gap resolution

---

## MCP API Scope

```
MCP API: sap.sf:apiResource:PLTGenericObjects:v1
MCP tool scope: read-write
Resources in scope: JobProfile, JobProfileSection, JobProfileTemplate, JobFamily, JobFunction, JobLevel, JobCode
```

```
MCP API: sap.sf:apiResource:ECPositionManagement:v1
MCP tool scope: read-only
Resources in scope: Position, PositionMatrixRelationship
```

```
MCP API: sap.sf:apiResource:ECSkillsManagement:v1
MCP tool scope: read-only
Resources in scope: Skill, SkillProfile, Competency, CompetencyLibrary
```

```
MCP API: sap.sf:apiResource:RCMJobRequisition:v1
MCP tool scope: read-write
Resources in scope: JobRequisition, JobRequisitionFieldControls
```

---

## Business Instrumentation

- [ ] Implement business step instrumentation for all 6 milestones from the PRD using structured logging and OpenTelemetry custom spans in `assets/job-profile-builder-agent/app/agent_executor.py`:
  - **M1** — Source Intake: span `job_profile.source_intake`
  - **M2** — Gap Resolution: span `job_profile.gap_resolution`
  - **M3** — Profile Draft Generation: span `job_profile.draft_generation`
  - **M4** — Human Review & Approval: span `job_profile.human_review`
  - **M5** — Output Delivery: span `job_profile.output_delivery`
  - **M6** — Batch Run Completion: span `job_profile.batch_completion`
- [ ] Each span must emit the log statement defined in the PRD Milestones section on both achieved and missed paths
- [ ] See `../guidelines-agent-python.md` for the canonical Python instrumentation pattern (extract business logic from `stream()` into a plain async helper)
- [ ] Verify `bootstrap(app)` is called after `app = server.build()` in `main.py`

---

## MCP Tool Integration

- [ ] During API discovery, verify `api-discovery-results.md` exists at workspace root with ORD IDs for all 4 required APIs
- [ ] API spec files are already downloaded to `specification/job-profile-builder-agent/api-specs/`:
  - `PLTGenericObjects.edmx` — Generic Objects API (job architecture, templates, profiles)
  - `ECPositionManagement.edmx` — Position Management API
  - `ECSkillsManagement.edmx` — Skills Management API
  - `RCMJobRequisition.edmx` — Job Requisition API
- [ ] Invoke `mcp-translation-file` skill for each of the 4 EDMX files; outputs land in `specification/job-profile-builder-agent/mcps/<api-spec-stem>/`
- [ ] Invoke `setup-solution` skill to create and register one MCP server asset per translated API
- [ ] Wire MCP tool loading in `agent.py` using `get_mcp_tools()` from the `mcp_tools` module — NEVER import directly from `sap_cloud_sdk.agentgateway`
- [ ] Add all 4 MCP server ORD IDs to the agent's `asset.yaml` under `requires` — read the exact `ordId` from each generated `asset.yaml` using `grep '^ordId:' assets/<mcp-server-asset-name>/asset.yaml`; never invent or guess ORD IDs
- [ ] After `mcp-translation-file` and `setup-solution` complete, generate `mcp-mock.json` using the `mcp-mock-config` skill

---

## Testing

- [ ] `conftest.py` sets only `IBD_TESTING=true` — this causes the agent to use mock MCP tool results during tests
- [ ] Write unit tests in `assets/job-profile-builder-agent/tests/` — one per tool:
  - `test_intake_tool.py` — test text extraction, file parsing, clone instruction, verbal input
  - `test_gap_resolution_tool.py` — test SF lookup success path and fallback to user Q&A
  - `test_generate_profile_tool.py` — test template section generation and guardrail check
  - `test_deliver_profile_tool.py` — test all 3 output modes and API-write fallback to CSV
  - `test_batch_process_tool.py` — test batch parsing, per-role completion, flagging, summary
  - `test_guardrail_check.py` — test discriminatory language detection and prompt injection detection
  - `test_find_similar_profiles_tool.py` — test similarity search and top-3 result return
  - `test_link_requisition_tool.py` — test requisition lookup and profile linkage
- [ ] Write one integration test `test_end_to_end.py` executing a full single-profile flow: paste input → gap resolution → draft generation → review approval → CSV export delivery
- [ ] Run `pytest` from `assets/job-profile-builder-agent/` (no args) — if coverage < 70%, add tests until threshold is met
- [ ] Run `pytest` again from `assets/job-profile-builder-agent/` (no args) to generate final `test_report.json`
- [ ] Verify `test_report.json` exists in `assets/job-profile-builder-agent/` — if not, run pytest again until it does
