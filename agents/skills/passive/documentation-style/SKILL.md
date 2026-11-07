---
name: documentation-style
description: Documentation, prose, wording, terminology, examples. Apply concise evidence-driven writing conventions when enabled; use polish-docs for an onboarding redesign.
metadata:
  category: passive
---

# Documentation style

Apply these defaults to the documentation being written or edited. Preserve page purpose and canonical terminology.

`README.md` serves humans: make it marketing-centric, leading with concrete value, credible proof, and a clear next action. `AGENTS.md` serves computers: make it utility-centric, prioritizing precise instructions, routing, constraints, and decision rules. Keep promotional prose out of AGENTS and agent operating procedures out of the README; neither audience benefits from unsupported claims.

Use [scratch records](../scratch-space/SKILL.md) only for unresolved documentation work or evidence needed to resume it. Keep settled conventions in their canonical documentation; do not log prose edits.

- **Identity, purpose, action:** identify what the product or feature is, the reader's problem it addresses, and how to use it. A capability list answers what, not why; connect capabilities to concrete needs without inventing benefits.
- **Context before action:** introduce each section with the product-specific premise that explains why the reader is there. A heading, option comparison, or “paste this prompt” is not that premise. One shared introduction can orient several options; then give the applicable commands or prompts.
- **Concision preserves understanding:** cut repetition and redundant walkthroughs, not identity, rationale, or necessary context. Explain unfamiliar categories before listing their members. Use headings that name the content and descriptions that state concrete behavior.
- Give each page a clear job. Tutorials teach through a result, how-to guides support a task, references specify behavior, and explanations develop understanding. Cross-link these page types; avoid mixing their purposes.
- State concrete capabilities and limits. No hand-waving, empty superlatives, exaggerated benefits, or unsupported claims of ease. Label illustrative data and distinguish roadmap from shipped behavior.
- Use descriptive sentence-case headings, short connected paragraphs, numbered sequences, and bullets for parallel choices. Use consistent names and units.
- Make examples usable: label code blocks, distinguish input from output, and explain substitutions. Use descriptive links to canonical detail rather than duplicating it.

Section introduction: “Dev Skills is designed to be installed in your project or agent. Copy the applicable prompt below into your coding agent and let it do the rest.” The first sentence establishes the product’s installation model; the second gives the action.

Illustrative purpose: “To reconcile exports whose rows arrive in different orders, Rowdiff matches records by customer ID and reports added, removed, and changed records.” This connects the capability to the reader’s task.

Apply conventions locally; a local edit does not authorize a documentation overhaul.
