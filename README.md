# Nihongo lemmatization data

Editable German, French, Spanish, Russian and Dutch form/lemma tables used by
Nihongo and Nihongo Lessons. Normalization version:
**simplemma-2.0.0-nihongo-2**. These are Simplemma 2.0.0 tables with the explicit
changes in `Tools/corrections.json`; they do not include Nihongo dictionary
definitions, example sentences, or user data.

Download the [matching editable data archive](https://github.com/clindsay3/nihongo-lemmatization-data/releases/download/simplemma-2.0.0-nihongo-2/simplemma-2.0.0-nihongo-2-data.tar.gz) or browse the
[versioned source materials](https://github.com/clindsay3/nihongo-lemmatization-data/tree/simplemma-2.0.0-nihongo-2). Both are publicly accessible
without authentication or a Nihongo subscription.

## Files

- `data/*.tsv`: complete corrected UTF-8 form/lemma pairs, sorted by form.
  Lines beginning with `# ` are notices; remaining lines have two tab-separated
  fields. Identity mappings are intentional.
- `resources/`: original license texts, source credits, the written offer, and
  provenance identifying the exact SML2 tables bundled in the apps.
- `Tools/`: the generation tools and corrections. Python is used to generate
  data; it is not part of the apps.
- `releases/simplemma-2.0.0-nihongo-2-data.tar.gz`: the matching editable data,
  corrections, provenance and notices in one downloadable archive.
- `SHA256SUMS`: checksums of the prepared files, excluding itself.

## Licenses

Read `resources/NOTICES.txt` first. Simplemma's implementation is MIT licensed.
Nihongo's generation tools are also offered under MIT; see `TOOLS-LICENSE.txt`.
Nihongo's correction contributions and database rights are offered under ODbL
1.0. Underlying contents retain their applicable source licenses, including
LGPL-LR, CC BY 4.0 and CC BY-SA. This is not a blanket MIT or ODbL license for
all third-party contents. Original credits and full license texts are preserved
in `resources/`, including the UD dataset source notices and CC BY-NC-SA 4.0
text. `UD-SOURCE-NOTICES.txt` describes the documented override-generation
inputs and Wikidata fill. Simplemma does not provide per-entry source
attribution; including a source notice does not identify the origin of each
mapping or grant additional permissions over third-party contents.

The data is supplied without warranty, under the applicable license disclaimers.
Contact **support@nihongo-app.com** for materials matching an app version or
for the written offer; include the app name, version and normalization version.

## Reproduce the bundled tables

Requires Python 3 and the official `simplemma-2.0.0-py3-none-any.whl` from
[PyPI](https://pypi.org/project/simplemma/2.0.0/#files). No third-party Python
packages need to be installed. The generator verifies the wheel's SHA-256:

`db33b15f5aed6485a748ce34d1f510ca760af2633289ab9a8493e2afa785c352`

Run from this repository's root:

```sh
mkdir -p generated
python3 Tools/generate_bundled_resources.py \
  --wheel /path/to/simplemma-2.0.0-py3-none-any.whl \
  --output resources \
  --rules-output generated/SimplemmaRuleData.swift \
  --source-archive generated/simplemma-2.0.0-nihongo-2-data.tar.gz
```

Compare the generated SML2 hashes with `resources/provenance.json` from the
published version (save a copy before regeneration). A gzip container's timestamp
may differ; the editable member contents and bundled table hashes identify the
data. Changing corrections or lookup behavior requires a new normalization
version and corresponding app search indexes.

Keep old version archives, notices, checksums and app-version associations
available when publishing a new version. A later correction does not replace
the materials for an earlier distributed app.
