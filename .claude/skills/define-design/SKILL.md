---
name: define-design
description: Guides a product owner through defining or revising their brand and application design using product context, inspiration, and visual feedback. Use when establishing a fork's design direction or deliberately reconsidering an existing one, rather than for routine UI implementation.
---

# Define brand and application design

Help the user make design decisions they can recognize in a real application. Produce an agreed brief in `docs/product/design.md` and a representative visual reference. The template's appearance is provisional; it does not express the fork owner's preferences.

## Establish context

Read `docs/product/overview.md`, `docs/product/glossary.md`, `docs/product/design.md` if present, the relevant PRDs, and representative app screens. Distinguish filled-in product decisions from scaffold instructions. Preserve existing brand decisions unless the user wants to revisit them.

Find out who uses the product, what they need to accomplish, how often and where they use it, which surfaces matter, and what brand assets or constraints already exist. For an established product, identify the scope of the redesign.

Ask one or two related questions at a time, adapting to the answers. Skip questions already answered by the documents or conversation. Use ordinary language and concrete situations; do not require design vocabulary or a long questionnaire. When the user is unsure, offer examples and explain the consequences.

## Explore inspiration

Invite products, brands, websites, screenshots, or other visual references the user admires, including examples outside their industry. Ask for dislikes as well. References are optional; continue from product context when none are available.

- Inspect supplied links or images with available tools. If a reference is inaccessible, say so and ask for a screenshot or description; do not claim to have seen it.
- Discuss specific observations: typography, color, imagery, layout, information density, navigation, interactions, and writing. Ask which qualities the user actually wants to carry over.
- Separate visual identity from application behavior. Liking a brand's illustrations does not establish a preference for its navigation or its product's usability.
- Record what to borrow, what to avoid, and why each reference fits the intended audience and tasks. A reference is inspiration, not an instruction to reproduce the entire product or reuse its assets.
- When references conflict, explain the tension and help the user choose which should guide the relevant decision.

Separate observations, user-confirmed preferences, and agent suggestions. Never silently promote an interpretation into a decision.

## Develop a direction

Explore the intended impression, voice, density, hierarchy, and interaction style through the user's actual tasks. Turn words such as "friendly" or "professional" into observable choices and examples of UI copy.

If the direction is uncertain, propose two or three meaningfully different approaches grounded in the conversation. Explain what each supports and what it trades away. Vary layout, typography, density, or interaction where appropriate, rather than presenting palette swaps. If the user already has a clear brand, develop it directly.

Show alternatives using the same representative product screen and realistic content so the user can compare them. Use the repository's available frontend tools for previews; keep experiments separate from production routes. A local mockup or screenshot is sufficient; do not depend on a particular agent platform or external design service.

Ask what works and what does not, refine the direction, and get the user's choice before treating it as agreed. If they delegate a decision, record that delegation and the reasoning. A lack of response does not select a direction.

## Exercise the application design

Try the selected direction on the relevant primary task, a dense view or long-content case, a form, and loading, empty, error, success, pending, and disabled states. Include small screens and native behavior for the surfaces in scope.

Resolve decisions as they become relevant:

- Brand expression: identity assets, imagery or illustration, color roles, typography, and icon treatment.
- Layout: hierarchy, navigation, information density, spacing, surfaces, borders, and radii.
- Behavior: feedback, motion, form interactions, and light/dark mode behavior.
- Language: voice, terminology, amount of explanation, and concrete examples.
- Accessibility: legibility, contrast, keyboard and screen-reader use, touch targets, text scaling, and reduced motion.

Do not impose a preferred palette, font pairing, minimalist copy, motion style, theme mode, or toast policy. Check that the design supports the product's tasks and accessibility needs. Preserve working auth, data access, and state handling when making previews.

## Record and hand off

Fold agreed decisions into `docs/product/design.md`, replacing superseded guidance rather than appending conflicting amendments. Keep it concise enough for a frontend agent to read before working. Include:

- The audience, usage context, intended experience, and scope.
- Inspiration references with the specific qualities adopted and excluded.
- Agreed visual, interaction, and language decisions, with concrete values or examples where settled.
- A representative visual reference saved in the repository and linked from the brief. Store supporting artifacts under `docs/product/design/` when needed.
- Platform differences, accessibility requirements, and relevant component or token locations.
- Open questions and provisional recommendations, clearly separated from agreed decisions.

Use `docs/product/glossary.md` for shared terminology and the owning PRD for changes to product requirements; the design brief does not replace either. Follow the PRD synchronization workflow when a PRD changes.

If the session ends before selection, save the useful findings and unresolved choices with their status. Do not label an unfinished brief or an unreviewed preview as approved. If visual tooling is unavailable or the user defers a preview, record that gap.

Design discovery does not by itself authorize a production redesign. When implementation is requested, use the web or mobile frontend skill to apply the agreed brief to tokens and shared components, verify the relevant states, and run repository checks. Keep enduring product choices in the brief rather than copying them into agent skills.
