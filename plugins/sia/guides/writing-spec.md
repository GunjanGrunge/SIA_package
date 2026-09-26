# Writing A Project's Own Spec

Authored after intake (`../AGENT.md` pipeline step 2), before any code
or deliverable content is produced. This guide describes the shape;
the content is entirely project-specific.

## Required Sections

1. **Problem / Goal** — what this project is for, in the user's terms.
2. **Architecture** — how the pieces fit together, at a level someone
   with no prior context can follow. For a software project this is
   components and data flow; for a document/deck project this is
   section structure and sourcing; for a design project this is the
   set of screens/artifacts and how they relate.
3. **Components** — each piece's single responsibility, its inputs, and
   what depends on it.
4. **Data Flow** — how information moves between components, end to
   end, for the project's main scenario.
5. **Error Handling** — what happens when an input is missing, invalid,
   or a step fails partway. For a non-software project this includes
   what happens when a required source document or approval is missing.
6. **Testing** — how the result will be verified before being called
   done: automated tests for software; a review/sign-off process and
   acceptance checklist for documents, decks, or designs.

## Process

One approved pattern, to avoid the two ways of gathering confirmation
in this guide and in `questioning-and-approval.md` pulling in different
directions:

- Follow `questioning-and-approval.md` while gathering the information
  this spec needs — batch every clarifying question into one round,
  don't drip-feed them.
- Draft the **complete** spec (all required sections) before asking for
  approval on any of it.
- Request **one structured approval round** on the complete draft —
  present it (in full, or section-by-section if that reads more clearly
  in chat, but as one continuous presentation, not paused for approval
  between sections) and ask for one round of feedback.
- **Exception:** if drafting surfaces a High-severity decision partway
  through (see `questioning-and-approval.md`'s severity table — an
  irreversible choice, a decision the rest of the spec depends on), stop
  and get that one decision confirmed before continuing to draft, rather
  than building the rest of the spec on an unconfirmed foundation. This
  is the only case where confirmation happens before the draft is
  complete.
- After writing the file, self-review it once: scan for placeholders
  ("TBD", "TODO"), internal contradictions between sections, and any
  requirement that could be read two ways — resolve ambiguity explicitly
  rather than leaving it for the next stage to guess at.
- Save to that project's own `docs/specs/YYYY-MM-DD-<topic>-design.md`.
