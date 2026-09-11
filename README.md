# acme

A scaffold for a new product on the Mention platform architecture. It is a complete, deployable
system with the business logic reduced to one thing: a user writes a note and the system
summarizes it with an LLM.

What is here: a Python shared kernel (`library/`), one domain-driven service (`services/notes`)
with a REST server, an event listener, a command executor, a scheduled job, and the outbox
triggers; an admin control plane (`admin/`) with backfills and seeding; a web app (`apps/web`), a
mobile app (`apps/mobile`), and an MCP server (`apps/mcp`); Terraform for a GCP folder with
operations, production, and per-branch feature projects; the `m` CLI that drives all of it; and
agent guidance under `.agents/`.

To start a product from it: create a repository from this template, work through `docs/rename.md`
to replace the `acme` placeholders, then `docs/bootstrap.md` to stand up GCP and ship. Day to day,
`AGENTS.md` is the entry point for the conventions and the commands.
