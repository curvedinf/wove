---
name: polish-docs
description: Polish README, onboarding, quickstart, documentation redesign. Improve first-use structure, persuasive evidence, and visual presentation; documentation-style covers ordinary prose edits.
metadata:
  category: activated
---

# Polish docs

Make the project's value and first-use path clear. Default to the README and directly related getting-started material.

Treat `README.md` as human-facing, marketing-centric documentation: earn adoption through concrete benefits and evidence. Put computer-facing, utility-centric routing and operating instructions in `AGENTS.md`; do not turn it into marketing copy.

Use [scratch records](../../passive/scratch-space/SKILL.md) only for unresolved documentation work or evidence needed to resume it. Keep settled conventions in their canonical documentation; do not log prose edits.

Use concrete, evidence-driven copy: no hand-waving, empty superlatives, or unsupported claims.

1. Read the project and documentation to establish the product, intended reader, and concrete problem it addresses. Distinguish supported benefits from inferred promises.
2. Compare introductions from successful projects with similar audiences. Choose relevant patterns to adapt; [reference examples](references/patterns.md) provide starting points.
3. Make the opening answer what this is, why the reader would use it, and how to start. Name the product category and connect its mechanism to the reader’s problem; neither a slogan nor a capability list supplies that explanation. Support the benefit with concrete evidence and one primary next action.
4. Follow the reader's adoption sequence: “Is this for me?” → “Why this?” → “Can I trust it?” → “How do I start?” Use a relevant example or demo as proof, address adoption barriers beside the call to action, then provide the shortest complete first-use path. When copy-paste prompts suffice, use them without an additional walkthrough. Link deeper reference and contributor material afterward.
5. Apply a coherent visual treatment using the conventions below and the existing documentation platform.
6. Read the page in order as a newcomer without conversation context. Check separately: can the reader identify the product, explain why it is useful, understand why each section is relevant, and take the next action? Do not count a feature description as a reason to use it. Verify claims, instructions, and rendered presentation as the task permits.

Use direct, reader-centered voice and the audience's terminology. Put proof beside each benefit; replace evaluative adjectives with observable behavior. Use descriptive headings and concrete skill or feature descriptions. Introduce unfamiliar categories by the need they address before listing members. Put a product-specific orientation sentence before installation prompts or choices; a shared introduction can serve both. Preserve this context when cutting repetition. For ongoing prose work, use [documentation-style](../../passive/documentation-style/SKILL.md).

## Visual conventions

Visual polish should make identity, behavior, and evidence easier to recognize and inspect.

- **Opening:** compose a compact wordmark, concrete value proposition, primary action, and real example or product image. Restrained gradients or illustration can establish identity without competing with the content.
- **Visual proof:** use crisp screenshots, annotated diagrams, or short demonstrations of supported behavior. Use consistent framing and evidence-specific captions; do not imply functionality with invented product imagery.
- **Consistency:** use a small palette, one recognizable icon style, and consistent spacing and borders. Keep reading surfaces quiet, with clear hierarchy and accessible contrast; reserve expressive decoration for the opening and transitions.
- **Useful components:** use icon cards for distinct routes, labeled code panels with copy controls where supported, and selective line highlighting. Keep commands and results distinct; use motion only to explain behavior or acknowledge interaction.
- **External grounding:** when naming adopted conventions, link authoritative external explanations. Describe the project’s adaptation accurately; internal files document implementation but do not independently substantiate the convention. Never imply endorsement or conformance beyond the evidence.
- **Trust signals:** place supported versions near installation, methodology beside benchmarks, and release status beside downloads. Link the license, changelog, and relevant limitations. Use a few meaningful badges, not a wall of implied endorsements.

For a GitHub README, favor a compact branded header, one useful visual, clean examples, and deliberate spacing. For a documentation site, add navigation cards, code controls, and theme support where the platform allows. Preserve readable text alternatives and narrow-screen usability.

## Examples

Illustrative opening for a fictional tool; assume the stated capabilities are supported:

> **Find added, removed, and changed records in CSV exports.**
>
> Recurring exports can reorder rows, making a line-by-line comparison misleading. Rowdiff is a CSV comparison tool that matches records by customer ID so you can identify actual record changes.
>
> **Review record changes**
>
> The report includes changed records and omits unchanged ones. Comparison runs locally; no upload or account required.
>
> **Compare your first exports**
>
> Try the included sample files, then compare your own.

The example immediately following that invitation, after installation:

```sh
rowdiff previous.csv current.csv --key customer_id
```

Example output:

```text
Added: 3 records
Removed: 1 record
Changed: 7 records
```
