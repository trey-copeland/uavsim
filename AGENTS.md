# Agent instructions

Follow **`GROK.md`** for all work in this repository (canonical process).

Key obligations:

- **GSD workflow** — roadmap → SPEC/design (mandatory for non-trivial work) → implement → review/merge
- **Research before execute** — `SPEC.md`, `docs/ARCHITECTURE.md`, heritage ME590 domain, then standard practice
- **Testing** — unit + integration; TDD default for new behavior; no MATLAB bit-parity
- **Heritage** — domain reference only; **no runtime MATLAB dependency**
- **Implementation map** — `docs/ARCHITECTURE.md` (packages, protocols, results, systems)
- **Stand-up path** — design docs in place → **repo skeleton** → Phase 1 SIL loop
- **Workflow** — vehicle → dynamics → SIL → export → HIL → compare (do not collapse plant I/O into control laws)

### Heritage path (domain only)

- WSL: `/mnt/d/Users/Trey/My Drive/Grad School UTK/Course Work/ME590/code`
- Windows: `D:\Users\Trey\My Drive\Grad School UTK\Course Work\ME590\code`

### Document map

| Doc | Role |
|-----|------|
| [`SPEC.md`](SPEC.md) | Product intent, user stories, acceptance (v0.2+) |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Layout, protocols, SIL/HIL, compare/export |
| [`GROK.md`](GROK.md) | Working agreements (process source of truth) |
| [`README.md`](README.md) | Human entry / status |

Do not invent package layout that contradicts `docs/ARCHITECTURE.md`. Update SPEC/ARCH when product or structural decisions change.
