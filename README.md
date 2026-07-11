# docinbox — Smart Document Inbox

Companion build for the *"Building a Smart Document Inbox on Local AWS"* tutorial
series (MiniStack + FastAPI + Ollama). This repo is built alongside the writing
so every part is verified working before it's published.

- **Writing plan & drafts:** `~/Documents/My_Study/private-docs/aws/ministack/`
- **Tagging convention:** one annotated tag per part (`part-01`, `part-02`, ...)
  marking the exact state a reader following that post should end up at.

## Workflow: building step by step, for readers to follow

All work happens as ordinary commits on `drafts` — one linear history, no
per-part branches, no duplicated folders per part. A reader can reproduce any
part two ways:

- **Checkout a checkpoint:** `git checkout part-03` reproduces the working
  state after Part 3 exactly.
- **See just what that part added:** `git diff part-02..part-03` (or the
  GitHub compare view `.../compare/part-02...part-03`, linkable straight from
  the blog post) shows precisely the diff that part's "Build" section walks
  through.

Rules of thumb:

1. Commit normally while building and verifying a part.
2. Once the code matches what the post describes, cut an annotated tag:
   `git tag -a part-0N -m "Part N — <title>"`.
3. **Tags are immutable once their post is published.** If a bug surfaces
   later, fix it forward with a new commit on `drafts` — don't rewrite a
   tag a reader may have already checked out.

## Structure (grows across the series)

```
docinbox/
├── app/          # FastAPI application (routes, config)
├── aws/          # portable AWS client factory (Part 1; Appendix B)
├── llm/          # OpenAI-compatible client -> Ollama, stands in for Bedrock (from Part 7)
├── worker/       # SQS consumer (from Part 5)
├── lambdas/      # Lambda source + layers, incl. LLM processing (from Part 7)
├── bootstrap/    # idempotent seed scripts (buckets/tables/queues/topics/params)
├── tests/        # pytest + fixtures (hardened in Part 10)
├── data/         # local MiniStack state — gitignored, not source
├── docker-compose.yml
└── Makefile
```

Folders are added as the part that introduces them is built, not pre-scaffolded.
