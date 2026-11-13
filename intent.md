# Job Profile Builder Agent

Automated AI agent for generating SAP SuccessFactors Job Profile Builder profiles from any source the user provides, eliminating manual data entry and accelerating talent acquisition.

## Business challenge

Clients must manually enter hundreds of thousands of job descriptions into SAP SuccessFactors Job Profile Builder — either field-by-field into template-governed shells, or by loading content from existing profiles into CSVs section by section. Each profile takes 30+ minutes, creating a critical bottleneck that delays recruiting when profiles are urgently needed to attach to requisitions and applications. Two methods exist today, both highly labor-intensive and time-sensitive.

## Business Goals & Success Criteria

| Metric | Baseline | Target | Timeline | Process / Capability | Source |
|--------|----------|--------|----------|----------------------|--------|
| Time to create a single job profile | ~30 minutes (manual) | < 2 minutes (agent-generated) | — | Job Profile Creation | user |
| Initial migration batch completion | — | As fast as possible | At agent go-live | Job Architecture Migration | user |
| Profiles created without manual re-entry | — | 100% agent-generated, human-reviewed | Ongoing | Job Profile Management | agent-derived |

## Key Milestones

1. **Source Intake** — Agent receives source data in any format (copy-paste, file upload, clone-existing instruction, verbal description) and identifies which job profile fields are present
2. **Gap Resolution** — Agent asks targeted clarifying questions for any missing required fields, drawing on the client's job architecture data in SuccessFactors where available
3. **Profile Draft Generation** — Agent produces a complete, template-compliant job profile draft using AI-generated content aligned to the correct template and sections
4. **Human Review & Approval** — User reviews the draft interactively; agent applies requested corrections before finalizing
5. **Output Delivery** — Agent writes the completed profile directly to SuccessFactors via API, or exports as a CSV ready for bulk upload, or delivers a formatted document — user selects at runtime
6. **Batch Processing** — Agent processes a list or file of roles and generates multiple profiles in a single batch run with no manual intervention per profile

## Business Architecture (RBA)

### End-to-End Process

Recruit to Retire

### Process Hierarchy

```
Recruit to Retire
└── Recruit to Onboard (generic)
    └── Attract and acquire talent (generic) [BPS-383]
        └── Manage job requisition
        └── Source and recruit candidates
        └── Offer job and hire candidate
        └── Request position
└── Develop to Grow (generic)
    └── Identify and grow talent (generic) [BPS-389]
        └── Plan career development
```

### Summary

Job profile creation and maintenance maps directly to the "Recruit to Retire" E2E process. Automating profile generation reduces the bottleneck in job requisition management and talent sourcing, and supports career development planning through a consistent, complete job architecture.

## Fit Gap Analysis

| Requirement (business) | Standard asset(s) found | API ORD ID | MCP Server ORD ID | MCP Server Version | Webhook API ORD ID | Data Product ORD ID | Gap? | Notes / assumptions |
|---|---|---|---|---|---|---|---|---|
| Read job architecture (job families, roles, codes) from SuccessFactors | SAP SuccessFactors Employee Central | `sap.sf:apiResource:PLTGenericObjects:v1` | — | — | — | — | No | Generic Objects API covers job architecture entities |
| Read Job Profile templates and sections | SAP SuccessFactors Employee Central | `sap.sf:apiResource:PLTGenericObjects:v1` | — | — | — | — | No | Job Profile Builder templates accessible via Generic Objects API |
| Read existing job profiles for cloning | SAP SuccessFactors Employee Central | `sap.sf:apiResource:PLTGenericObjects:v1` | — | — | — | — | No | Existing profiles readable via same API |
| Write completed job profiles to SuccessFactors | SAP SuccessFactors Employee Central | `sap.sf:apiResource:PLTGenericObjects:v1` | — | — | — | — | Maybe | Write support depends on Job Profile Builder API availability; fallback to CSV export |
| Read position data for context | SAP SuccessFactors Employee Central | `sap.sf:apiResource:ECPositionManagement:v1` | — | — | — | — | No | Position Management API available |
| Read skills / competency data | SAP SuccessFactors Employee Central | `sap.sf:apiResource:ECSkillsManagement:v1` | — | — | — | — | No | Skills Management API available |
| Attach job profiles to job requisitions | SAP SuccessFactors Recruiting | `sap.sf:apiResource:RCMJobRequisition:v1` | — | — | — | — | No | Job Requisition API available |
| AI content generation from mixed sources (paste, file, verbal) | No standard SAP tool | — | — | — | — | — | Yes | Core gap — requires custom AI Agent with LLM-based generation |
| Batch profile generation | No standard SAP tool | — | — | — | — | — | Yes | Core gap — requires custom agent batch processing capability |
| CSV export for bulk upload | No standard SAP tool | — | — | — | — | — | Yes | Must be built as an agent output mode |

### Key findings

- SAP SuccessFactors provides the necessary APIs to read job architecture, templates, existing profiles, positions, and skills — the data layer is well-covered
- No out-of-the-box SAP capability exists for AI-driven job profile content generation from mixed, unstructured source inputs
- Batch processing of job profiles is not natively supported — this is a key differentiator for the agent
- No MCP servers are currently available for SuccessFactors APIs; the agent will need direct OData API integration
- The agent must support flexible output modes (API write, CSV export, document draft) to accommodate different client workflows and SuccessFactors access levels
- CSV upload via the Job Profile Builder import mechanism is the safest fallback where direct API write is not supported

## Recommendations

### Job Profile Builder AI Agent

#### Executive Summary

AI agent automates SuccessFactors job profile creation from any source input

#### Recommended Solution

A conversational and batch-capable AI agent built on a Python A2A protocol runtime, integrated with SAP SuccessFactors APIs. The agent accepts job profile source data in any format (copy-paste, file upload, clone request, verbal description), resolves missing fields by querying the client's own SuccessFactors job architecture and templates, generates complete and template-compliant job profile content using an LLM, and delivers the result directly to SuccessFactors via API, as a bulk-upload CSV, or as a formatted document — at the user's choice. Batch mode enables processing an entire list of roles in a single run.

#### Problem Statement

Creating job profiles in SAP SuccessFactors Job Profile Builder requires manually entering or loading content for every section of every template — a process taking 30+ minutes per profile, making large-scale job architecture migrations and time-sensitive recruiting support prohibitively expensive in both time and labor.

#### Affected User Roles

- HR / Talent Acquisition team members
- Job Architecture owners / compensation analysts
- Hiring managers requesting profiles for open roles
- HR system administrators and implementation consultants

#### Important factors

##### Eliminates manual data entry at scale

The agent removes the primary cost driver — manual content entry — by generating structured, template-aligned profile content automatically, reducing per-profile effort from 30+ minutes to under 2 minutes.

##### Flexible source input

The agent accepts whatever the user provides: a pasted job description, an instruction to clone an existing profile, a dropped document, or a verbal description. It asks follow-up questions only when required data is missing.

##### Multiple output modes for maximum compatibility

By supporting direct API write, CSV bulk export, and document draft, the agent works regardless of the client's SuccessFactors configuration or access level, future-proofing adoption.

##### Batch capability for migrations

The agent processes entire batches of roles in one run, making it viable for initial migrations involving thousands of profiles — not just ongoing day-to-day use.

#### Potential risks

##### Job Profile Builder API write limitations

SuccessFactors Job Profile Builder may have limited or no direct OData write support for all profile sections. The CSV export mode is the designed fallback, but the API scope must be validated during specification.

##### Content quality and compliance

AI-generated content must align with the client's tone, terminology, and any regulatory requirements (e.g. equal opportunity language). A mandatory human review step is built into the milestone sequence to mitigate this.

##### Data volume for batch runs

Very large batch jobs (tens of thousands of profiles) may require rate-limit management and job-queuing logic to avoid API throttling.

#### Recommended solution category

AI Agent

#### Intent fit

92%
