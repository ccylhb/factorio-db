# FactorioDB

**Live site: <https://factorio.lootseer.com>**

Data sourced from the public wiki.factorio.com wiki and restructured for lookup.

## What this is

A fast, ad-light game database built as a fully static Astro site:
every page is pre-rendered HTML with structured data (JSON-LD), readable
in well under a second. Data is kept in plain JSON under `src/data/`,
scraped and cleaned from public wiki sources by the scripts in
`scripts/`, then compiled at build time.

## Why answer-first

Players search for concrete numbers, not wiki walls of text. Pages lead
with the answer (stats, drops, recipes) and link related items both ways,
including reverse-lookup and calculator tools where available.

## Data source

- [wiki.factorio.com](https://wiki.factorio.com) — public wiki, parsed and restructured
