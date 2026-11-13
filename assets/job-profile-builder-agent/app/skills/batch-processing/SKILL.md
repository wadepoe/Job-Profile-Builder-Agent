---
name: batch-processing
description: Instructions for processing a batch input of multiple job roles and generating SAP SuccessFactors job profiles for all of them in a single unattended run
---

# Batch Processing Skill

## When to Use This Skill

Load this skill when the user provides a list of roles or a CSV file and wants profiles generated for all of them without reviewing each one individually.

## Step 1: Parse the Batch Input

Accept one of the following formats:

### CSV Format
Expected columns (any order, header row required):
- `job_title` (required)
- `job_code` (optional — looked up from SuccessFactors if absent)
- `job_family` (optional)
- `job_function` (optional)
- `job_level` (optional)
- `template_id` (optional — defaults to client standard template if absent)
- `source_text` (optional — raw description to use as source content)

### Plain List Format
One role name or code per line. Agent uses the value as `job_title` and resolves all other fields from SuccessFactors.

### Validation
- Reject the batch if the file cannot be parsed.
- Reject rows where `job_title` is empty or whitespace.
- Report the rejection reason and continue with valid rows.

## Step 2: Confirm Batch Parameters Before Starting

Before processing, confirm with the user:
1. Total number of roles detected in the input
2. Default output mode for the batch (CSV export is the default unless specified)
3. Whether to auto-generate all profiles or pause for flagged roles at the end

## Step 3: Process Each Role

For each role in the batch:

1. Run the profile generation pipeline (see `profile-generation` skill):
   - Field extraction from `source_text` if provided
   - Gap resolution from SuccessFactors
   - Template lookup and section generation
   - Content guardrail check

2. Track the outcome:
   - `generated` — profile completed successfully
   - `flagged` — profile could not be completed due to unresolvable missing fields; record which fields
   - `failed` — an API error prevented processing; record the error

3. Do NOT stop the batch when a single role fails or is flagged. Continue processing the remaining roles.

## Step 4: API Rate-Limit Management

For every SuccessFactors API call within a batch run:

1. On HTTP 429 (Too Many Requests) or 503:
   - Wait: start at 1 second, double on each retry (1s → 2s → 4s → max 30s)
   - Maximum 3 retries per call
   - If all retries fail, mark the role as `failed` and continue

2. Between roles, add a 200ms pause to reduce burst load.

## Step 5: Deliver Batch Output

After all roles are processed:

1. Deliver the output in the selected mode:
   - **CSV export (default):** compile all generated profiles into a single SuccessFactors-compatible CSV file
   - **API write:** write each completed profile to SuccessFactors in sequence
   - **Document:** return a ZIP of individual profile documents

2. Return the batch summary:

```
Batch Processing Summary
========================
Total roles submitted:    {total_roles}
Profiles generated:       {profiles_generated}
Profiles flagged:         {profiles_flagged}
Profiles failed:          {profiles_failed}

Flagged roles (need manual input):
  - {role_title}: missing fields: {missing_fields}

Failed roles (API errors):
  - {role_title}: {error_message}
```

## Step 6: Offer Follow-Up

After delivering the summary:
- Offer to process the flagged roles interactively, one at a time
- Offer to retry failed roles
- Confirm the output file is ready for download/import
