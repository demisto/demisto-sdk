---
applyTo: "demisto_sdk/commands/content_graph/**/*.py"
---

# Copilot instructions — content graph

Read together with the repo-wide
[`copilot-instructions.md`](../copilot-instructions.md). This file specialises
guidance for the **content graph** subsystem
([`demisto_sdk/commands/content_graph/`](../../demisto_sdk/commands/content_graph)).

The content graph is a **Neo4j-backed typed model** of every content item
in a content repo (Pack, Integration, Script, Playbook, IncidentField,
ModelingRule, …) and the relationships between them
(USES, IN_PACK, HAS_COMMAND, IMPORTS, TESTED_BY, DEPENDS_ON, …). It powers
`validate`, `format`, `find-dependencies`, `prepare-content`, dependency
resolution, and many other commands.

## Layout

```
demisto_sdk/commands/content_graph/
├── content_graph_builder.py     # Orchestrates parse → load → relationships
├── content_graph_setup.py       # Typer CLI (`demisto-sdk graph ...`)
├── neo4j_service.py             # Local Neo4j lifecycle (docker-compose)
├── common.py                    # ContentType, RelationshipType, constants
├── commands/                    # `create`, `update`, `get-dependencies`, `get-relationships`
├── parsers/                     # File → unvalidated dict (per content type)
├── objects/                     # Pydantic v1 models surfaced to consumers
├── strict_objects/              # Strict variants used by `validate`
├── interface/                   # Neo4j queries (Cypher) wrapped as typed methods
├── images/                      # Image-related helpers
└── tests/
```

## Core concepts

- **`ContentType`** ([`common.py`](../../demisto_sdk/commands/content_graph/common.py)) —
  enum of every content type the graph knows about.
- **`RelationshipType`** ([`common.py`](../../demisto_sdk/commands/content_graph/common.py)) —
  enum of edge labels (`USES`, `IN_PACK`, `HAS_COMMAND`, …).
- **Parsers** ([`parsers/`](../../demisto_sdk/commands/content_graph/parsers))
  read a file from disk and produce a raw dict + a list of relationships to
  be created. There is one parser per content type. Parsers should be
  cheap and side-effect free.
- **Objects** ([`objects/`](../../demisto_sdk/commands/content_graph/objects))
  are **Pydantic v1** `BaseModel`s representing nodes. They expose typed
  fields (`name`, `path`, `marketplaces`, `fromversion`, `toversion`, …)
  and convenience methods.
- **Strict objects** ([`strict_objects/`](../../demisto_sdk/commands/content_graph/strict_objects))
  add stricter field validation; used by `validate`. Don't put business
  logic here — only schema.
- **Interface** ([`interface/`](../../demisto_sdk/commands/content_graph/interface))
  exposes typed query methods. **All** Cypher belongs here, not in
  command code.

## Hard rules

1. **Pydantic v1.** Do not use v2 syntax. Use `@validator`, `class Config`,
   `.dict()`, `__root__`. The migration plan lives in
   [`plans/pydantic-v2-migration.md`](../../plans/pydantic-v2-migration.md);
   do not pre-empt it.
2. **No raw Cypher outside `interface/`.** Command code, validators, and
   parsers must call typed methods on the interface. If a query is
   missing, add a method on the interface (with a unit test) and call
   that.
3. **Parsers are pure.** They take a `Path`, return a dict + relationships.
   No DB access, no network, no logging at INFO+ levels.
4. **Objects are immutable from the consumer's perspective.** Treat them
   as read-only after construction. Don't mutate fields from validators
   or commands.
5. **`marketplaces` is plural.** Every content object can target multiple
   marketplaces (`xsoar`, `marketplacev2`, `xpanse`, `xsoar_saas`). Use
   the `MarketplaceVersions` enum from
   [`demisto_sdk/commands/common/constants.py`](../../demisto_sdk/commands/common/constants.py).
   Never assume a single marketplace.
6. **`fromversion` / `toversion` matter.** When iterating content, respect
   version filters; many graph queries already accept a `marketplace` /
   `version` parameter.
7. **Neo4j must be assumed remote.** Don't read Neo4j data directories
   directly; use the bolt driver via the interface.

## Adding a new content type

1. Add it to `ContentType` in
   [`common.py`](../../demisto_sdk/commands/content_graph/common.py).
2. Create a parser in
   [`parsers/<your_type>.py`](../../demisto_sdk/commands/content_graph/parsers).
3. Create the object in
   [`objects/<your_type>.py`](../../demisto_sdk/commands/content_graph/objects)
   (Pydantic v1 model inheriting from the appropriate base —
   `ContentItem`, `BaseContent`, etc.).
4. Create the strict variant in
   [`strict_objects/<your_type>.py`](../../demisto_sdk/commands/content_graph/strict_objects).
5. Wire it into [`content_graph_builder.py`](../../demisto_sdk/commands/content_graph/content_graph_builder.py).
6. Expose interface methods in
   [`interface/`](../../demisto_sdk/commands/content_graph/interface) for any
   queries consumers will need.
7. Tests under
   [`demisto_sdk/commands/content_graph/tests/`](../../demisto_sdk/commands/content_graph/tests),
   using `TestSuite` builders to construct fixtures.

## Adding a new relationship type

1. Add it to `RelationshipType` in
   [`common.py`](../../demisto_sdk/commands/content_graph/common.py).
2. Emit it from the relevant parser(s).
3. Add a typed query method in `interface/` if consumers need to traverse
   it.
4. Test that the relationship is created and traversable end-to-end.

## Don'ts

- Don't import `neo4j` types in command code or validators — wrap them in
  the interface and return plain Python types or graph objects.
- Don't use `pydantic.v1` shim or `pydantic.v2` features.
- Don't introduce blocking I/O in object property accessors.
- Don't silently swallow Neo4j connection errors. Surface a clear error
  pointing the user to `demisto-sdk graph create`.

## Local Neo4j

Local development uses a docker-compose-managed Neo4j started by
[`neo4j_service.py`](../../demisto_sdk/commands/content_graph/neo4j_service.py).
Tests **must mock the Neo4j driver** rather than starting a container.
