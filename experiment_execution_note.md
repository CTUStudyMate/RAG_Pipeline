# RAG Experiment — Execution Note

## Operating rules

- Codex prepares files/configs/scripts and exact commands; the user runs chunking,
  answer generation, evaluation, and score aggregation commands.
- Read-only checks require no approval. Before every state-changing large step,
  preview the complete changes and wait for approval; then report changed paths
  and locations using `/` separators.
- Schedule independent work as soon as its prerequisites are ready.
- Reuse a valid existing answer/evaluation result; place it in the corresponding
  report folder instead of rerunning it.

## Configuration inheritance

Never revert to a default config. Each new stage starts from the selected config
of the prior stage and changes only the parameter being evaluated.

1. Stage 1 selects chunk strategy: fixed size vs RC vs HSF (size 600, normal,
   budget 2000).
2. Stage 2 keeps the selected Stage-1 chunk setup and selects the final retrieve
   strategy. It may be normal or a multistage variant; it is not assumed to be
   multistage.
3. Stage 3 keeps Stage-1 chunk strategy + Stage-2 retrieve choice and selects
   chunk size (400, 600, 800).
4. Stage 4 keeps all selected upstream settings and selects budget (1600, 2000,
   2400).

## Shared inputs and reporting locations

- Datasets:
  - `RAG_Pipeline/notebooklm_generated_dataset.json`
  - `RAG_Pipeline/studyguide_based_dataset.json`
- Report answers:
  `RAG_Pipeline_Evaluation/final_exp_for_report/answers/<stage>/<dataset>/`
- Report evaluations:
  `RAG_Pipeline_Evaluation/final_exp_for_report/eval_results/<stage>/<dataset>/`
- Dataset directory names: `notebooklm`, `studyguide`.
- Canonical stage folders:
  - `stage1__chunk_strategies`
  - `stage2__retrieve_strategies`
  - `stage3__chunk_size`
  - `stage4__retrieve_budget`

## Stage checklist

### Stage 1 — chunk strategies

- Chunked corpora and normal-retrieve/2000 answer sets already exist.
- Copy each answer CSV to the Stage-1 report structure, configure
  `run_evals.py`, run both dataset evaluations, then configure
  `calculate_exp_score.py` for Stage 1.
- Choose one chunk strategy.

### Stage 2 — retrieve strategies

- Corpus is reused from the Stage-1 winner; normal is the existing baseline.
- Loop 1: make a clean experiment copy (no `__pycache__` or old CSVs), test
  multistage vector/BM25 `0.5/0.5`, generate two answer sets, evaluate only
  new results, and aggregate with the normal baseline.
- Choose a second retrieve candidate, repeat the loop, then select the final
  retrieve strategy from all candidates.
- Folder/config/run scripts must agree on chunk setup, retrieve type/weights,
  and budget. Point `pipeline_config.py` at the active experiment config.

### Stage 3 — chunk size

- Reuse valid 600 artifacts; create/chunk 400 and 800 for the selected chunk
  strategy.
- Each new chunk version needs unique storage/debug/log paths and PGDB/vector
  DB names including strategy, size, and creation date. Start `debug_data/`,
  `log/`, and `vectorchunks_storage/` empty; do not create `error.txt`.
- Use `assets/scripts_for_db/pgdb.md` for the three PGDB setup commands.
- Temporarily uncomment the chosen chunk runner; re-comment it after confirmed
  completion.
- Generate/evaluate 400 as soon as ready while 800 is being prepared; retain
  the exact Stage-2 retrieve selection for both. Aggregate 400/600/800.

### Stage 4 — retrieve budget

- Reuse corpus and valid 2000 results from Stage 3.
- Create answer/evaluation runs for 1600 and 2400, inheriting the full Stage-3
  selected setup and changing only budget. Aggregate 1600/2000/2400.

## Pre-run checks

- `pipeline_config.py` points at the intended active config.
- Experiment config points at the intended chunk-version config.
- Config, folder name, scripts, CSV names, and evaluation paths agree on all
  selected parameters.
- Both datasets have distinct answer and evaluation outputs.
- No stale `phase*` report path is used where the canonical `stage*` path is
  intended.
