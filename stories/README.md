# Stories

Prose published on the Stories page of the site. Each `.md` file here is a
verbatim snapshot of the canonical draft in Obsidian
(`~/obsidian/Fiction Writing/The Cabin/`):

- `the-cabin.md` — The Cabin (Elli's story)
- `no-further.md` — No Further (Nika's story)

The Obsidian copies are the source of truth. When a draft changes, refresh the
snapshot wholesale rather than patching lines here:

```bash
cp ~/obsidian/Fiction\ Writing/The\ Cabin/The\ Cabin.md stories/the-cabin.md
cp ~/obsidian/Fiction\ Writing/The\ Cabin/No\ Further.md stories/no-further.md
```

The site pages (`the-cabin.html`, `no-further.html` at repo root) fetch these
files at runtime and render them client-side, so a markdown change is all a
prose tweak needs. The renderer understands:

- blank lines as paragraph breaks
- a line containing only `*` as a scene break
- `*text*` as italics
