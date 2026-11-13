---
name: profile-generation
description: Step-by-step instructions for generating a template-compliant SAP SuccessFactors job profile from provided source data, including field extraction, gap identification, content generation, and guardrails
---

# Job Profile Generation Skill

## When to Use This Skill

Load this skill when the user wants to create or generate a job profile, whether from pasted text, a document, a verbal description, or by cloning an existing profile.

## Step 1: Extract Fields from Source Data

Identify the following job profile fields from the source input:

### Required Fields
- `job_title` — the name of the role
- `job_code` — the unique job code identifier
- `job_family` — the job family this role belongs to
- `job_function` — the job function within the family
- `job_level` — the grade or level (e.g., P1, M2, IC3)
- `template_id` — the Job Profile Builder template to use

### Standard Profile Sections (populate from source if present)
- `purpose` — brief statement of why the role exists
- `responsibilities` — key duties and accountabilities
- `qualifications` — education and experience requirements
- `competencies` — behavioural and technical competencies
- `skills` — specific technical or functional skills
- `physical_requirements` — any physical demands (if applicable)
- `additional_information` — any other relevant content

For each field, assign a confidence flag:
- `found` — explicitly stated in the source
- `inferred` — reasonably deducible from context
- `missing` — not present; must be resolved

## Step 2: Identify and Resolve Gaps

For each `missing` field:

1. First attempt to resolve from SuccessFactors data:
   - Job family, function, level, code → query Generic Objects API
   - Position context → query Position Management API
   - Competencies/skills → query Skills Management API

2. If SuccessFactors lookup returns a unique match, pre-fill the field and mark as `sf_lookup`.

3. If SuccessFactors lookup returns multiple matches, present options to the user.

4. If SuccessFactors has no data, ask the user ONE targeted question per missing field. Example: "What job family does this role belong to?"

5. Never ask for a field that can be looked up in SuccessFactors.

## Step 3: Read the Assigned Template

Once `template_id` is known:

1. Call the Generic Objects API to retrieve the template definition.
2. Note every section defined in the template and its content rules.
3. Identify which sections are mandatory vs optional.

## Step 4: Generate Profile Content

For each template section:

1. Use any `found` or `inferred` data from the source as the primary input.
2. For sections with no source data, generate content using the LLM guided by:
   - The job title, family, level, and function for context
   - SAP SuccessFactors best practices for job profiles
   - The section's content rules from the template
3. Annotate each section with its source: `sf_lookup`, `doc_extracted`, or `ai_generated`.

## Step 5: Apply Content Guardrails

Before presenting any section to the user, check for:

### Prohibited Language Patterns
- Age references: "young", "recent graduate", "X years old", "energetic", "digital native"
- Gendered terms: "he/him", "she/her", "manpower", "chairman", "stewardess"
- Protected class references: religion, race, national origin, disability status
- Discriminatory requirements: physical requirements not essential to the role

### Action on Detection
- Remove or rephrase the flagged content.
- Use inclusive language: "candidate", "applicant", "they/them" as default pronouns.
- If uncertain, flag the section for user review rather than silently editing.

## Step 6: Present Draft for Review

Present each section clearly labelled with:
- Section name
- Generated content
- Source annotation (sf_lookup / doc_extracted / ai_generated)

Ask the user to review each section and either:
- Approve it as-is
- Request a specific change (agent regenerates only that section)

Proceed to output delivery only after the user explicitly approves the full draft.

## Content Quality Rules

- Write in clear, professional language
- Use active voice for responsibilities ("Manages", "Leads", "Develops")
- Quantify where possible ("Manages a team of 5-10 engineers")
- Avoid jargon unless it is standard in the industry for this role
- Keep responsibilities to 6-10 bullet points
- Keep qualifications to required vs preferred categories
- Never fabricate metrics, salary ranges, or organisational data
