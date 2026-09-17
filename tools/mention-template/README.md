# mention-template

Create an independent application repository on AWS, GCP, or Azure, then continue
setup in your installed Claude Code or Codex. Use your existing agent account;
the launcher does not collect credentials or run its own agent service.

The initial beta command, once published, is:

```sh
uvx --from mention-template==0.1.0b1 mention-template
```

Equivalent:

```sh
uv run --no-project --with mention-template==0.1.0b1 mention-template
```

Install uv, Git, and either Claude Code or Codex first. Run in a macOS, Linux,
or WSL terminal. The launcher asks for the agent, cloud, and destination:

```sh
mention-template --agent claude --cloud aws --directory ./my-project
mention-template resume ./my-project --agent codex
```

With uvx, place those arguments after `mention-template`. Agent installation and
sign-in are guided through the agent's official setup process. Node, pnpm,
Terraform, Docker, and cloud tools are installed as needed during project setup;
they are not launcher dependencies.

Each launcher release pins three template snapshots and verifies their checksums.
New projects have a fresh main branch, no remote, and no upstream history.
Nothing is published or deployed merely by creating a project. Resume uses saved
configuration and diagnostics, so you can switch agents without transferring chat
history. Exit the agent normally or use Ctrl-C; the printed resume command remains
valid even when sign-in fails.

This is beta software. Automated export and setup checks do not establish successful
cloud deployment, authentication, or summarization. See the generated project's
`docs/setup-verification.md` for the actual verification status.
