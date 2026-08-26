# docinbox — Smart Document Inbox

Companion build for the [*"Building a Smart Document Inbox on Local AWS"*](https://medium.com/@chuan-zhang/building-a-smart-document-inbox-on-local-aws-part-1-foundations-9ec6682bebd5) tutorial
series (MiniStack + FastAPI + Ollama). This repo is built alongside the writing
so every part is verified working before it's published.

- **Tagging convention:** one annotated tag per part (`part-01`, `part-02`, ...)
  marking the exact state a reader following that post should end up at.

## Running the app

Two supported options. They are interchangeable - same code, same MiniStack,
same `localhost:8000` - so pick whichever suits you and switch any time.

### Option A - uvicorn on the host (MiniStack in Docker)

The lightest loop: Python runs in your own venv, so debuggers, breakpoints and
`pytest` all work with no container in the way.

```bash
cp .env.example .env         # AWS_ENDPOINT_URL stays http://localhost:4566
pip install -r requirements-dev.txt
make up                      # MiniStack only
make seed                    # buckets/tables/params/secrets
make run                     # uvicorn app.main:app --reload
```

### Option B - the app in Docker too

Nothing to install but Docker, and you get the app in the shape it would ship
in. `Dockerfile` builds the image; the `app` service in `docker-compose.yml`
runs it next to MiniStack.

```bash
make docker-up               # build + start MiniStack and the app
make docker-seed             # seed from inside the app container
make docker-logs             # tail the app's logs
```

`make health` and `curl localhost:8000/...` work exactly as in Option A.
`make down` stops everything either way.

Two things worth knowing about Option B:

- **The endpoint URL differs inside the network.** Compose sets
  `AWS_ENDPOINT_URL=http://ministack:4566` for the app service, overriding the
  `localhost:4566` in your `.env` - containers reach MiniStack by service name,
  not through the host.
- **`.env` is not baked into the image.** It's in `.dockerignore`; compose reads
  it at run time (and the file is optional - `app/config.py` has defaults).

The app service bind-mounts `app/` and `bootstrap/` and runs uvicorn with
`--reload`, so edits on the host restart the container's app just like Option A.
The image's own `CMD` has no `--reload` - that's the deployable shape, and
compose overrides it for development.

> **Presigned URLs are signed for a different endpoint than the app calls.**
> Under Option B the app reaches MiniStack at `ministack:4566`, but a URL from
> `/documents/{id}/download_url` is followed by your browser or Postman on the
> host, where that name does not resolve. Compose therefore also sets
> `PUBLIC_AWS_ENDPOINT_URL=http://localhost:4566`, and the app signs URLs with
> a second S3 client bound to it. Option A needs no such setting - there, the
> app and the caller already share one address, exactly as in real AWS.

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
├── Dockerfile    # the app image (Option B above)
├── docker-compose.yml
└── Makefile
```

Folders are added as the part that introduces them is built, not pre-scaffolded.
