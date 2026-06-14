# HSF Algorithm - Visual Guides & Examples

## 1. Algorithm Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    HSF CHUNKING PIPELINE                            │
└─────────────────────────────────────────────────────────────────────┘

INPUT: PDF Document
  │
  ├─ PHASE 1: PDF Parsing (Docling)
  │   Extract: [Text, Images, Tables, Metadata]
  │   └─ Output: Flat list of atomic elements
  │
  ├─ PHASE 2: Build Document Hierarchy
  │   Extract: Table of Contents
  │   Build: Tree structure respecting heading levels
  │   └─ Output: Hierarchy tree (Chapter → Section → Subsection)
  │
  ├─ PHASE 3: Associate Atomics ↔ Hierarchy
  │   Match atomic elements to tree nodes
  │   └─ Output: Each node knows its content (gold_units)
  │
  ├─ PHASE 4: Compute Token Counts
  │   Bottom-up aggregation: node_token = children_tokens + gold_units_tokens
  │   └─ Output: Tree with token_count for each node
  │
  ├─ PHASE 5: Hierarchical Chunking (MAIN ALGORITHM)
  │   Recursive partitioning based on token constraints
  │   ├─ If node <= MAX_TOKEN: Create 1 chunk
  │   ├─ Else if has children: Recurse into children
  │   └─ Else (leaf > MAX): Apply semantic splitting
  │       └─ Split by subheadings
  │       └─ Fallback to fixed-size if needed
  │       └─ Output: Multiple chunks respecting [MIN, MAX] token range
  │
  ├─ PHASE 6: Image Description Generation (LLM)
  │   For each image in chunks: generate retrieval-optimized description
  │   └─ Output: {img_id, description_text}
  │
  └─ PHASE 7: Index & Store
      ├─ Vector DB (Chroma): Store embeddings + metadata
      ├─ PostgreSQL: Store text + BM25 index + images
      └─ Output: Chunk corpus ready for retrieval

OUTPUT: Indexed chunks ready for RAG retrieval
```

---

## 2. Token-Based Recursive Chunking

### Decision Tree: When to Split

```
NODE.token_count <= MAX_TOKEN?
│
├─ YES: ✓ Node fits in single chunk
│       └─ create_chunk(node) → [Chunk]
│
└─ NO: Node too large
    │
    ├─ Has children?
    │  │
    │  ├─ YES: Recurse into children
    │  │       FOR EACH child:
    │  │           build_chunks(child) ✓ Children may fit
    │  │       └─ Combines chunks from all children
    │  │
    │  └─ NO: Leaf node too large
    │          └─ Split using semantic boundaries
    │              ├─ Split by subheadings (nottoc)
    │              ├─ For each block:
    │              │   IF block.token <= MAX: Create chunk
    │              │   ELSE: chunk_by_semantic_units(block)
    │              └─ Fallback: fixed_size_split(atomic)
```

### Example: Document Structure vs Token Distribution

```
CHAPTER 1 (ROOT)
├─ Section 1.1 [2000 tokens]     MAX_TOKEN=600
│  └─ 2000 > 600? YES, has children
│     ├─ Subsection 1.1.1 [700]  → Too large
│     │  └─ Split by subheadings → [Chunk1-A: 400, Chunk1-B: 300]
│     └─ Subsection 1.1.2 [1300] → Too large
│        └─ Split by subheadings → [Chunk2-A: 550, Chunk2-B: 750]
│           └─ 750 > 600? YES, apply semantic units
│              └─ Sentence-level split → [Chunk2-B1: 600, Chunk2-B2: 150]
│
├─ Section 1.2 [400 tokens]      ✓ Fits in single chunk
│  └─ 400 <= 600? YES
│     └─ [Chunk3: 400 tokens]
│
└─ Section 1.3 [600 tokens]      Edge case (exactly at boundary)
   └─ 600 <= 600? YES
      └─ [Chunk4: 600 tokens]

TOTAL OUTPUT: 6 chunks, all within [MIN=200, MAX=600] tokens
```

---

## 3. Semantic-Aware Greedy Chunking (`chunk_by_semantic_units`)

### Algorithm State Machine

```
State: ACCUMULATING
├─ current_chunk = [].empty()
├─ current_token = 0
└─ FOR EACH atomic:
    │
    ├─ IF current_token + atomic_token < MAX_TOKEN:
    │    └─ MERGE atomic into current_chunk
    │        └─ current_token += atomic_token
    │
    └─ ELSE (adding would exceed MAX):
        │
        ├─ IF current_token >= MIN_TOKEN:
        │    ├─ FLUSH current_chunk → Output
        │    └─ START NEW chunk with atomic
        │        State → ACCUMULATING
        │
        ├─ ELSE (current chunk too small):
        │    │
        │    ├─ IF atomic_token < MAX_TOKEN:
        │    │    ├─ MERGE atomic anyway (sacrifice min)
        │    │    ├─ FLUSH → Output
        │    │    └─ START NEW chunk
        │    │
        │    └─ ELSE (atomic > MAX - extreme case):
        │         ├─ SPLIT atomic using fixed-size
        │         ├─ MERGE first_split with current_chunk
        │         ├─ FLUSH merged → Output
        │         ├─ OUTPUT remaining splits directly
        │         └─ START NEW chunk
```

### Example: Greedy Accumulation

```
Atomics: [A:100, B:250, C:150, D:300, E:100]
Config: MIN=200, MAX=600

Step 1: current=[],  token=0
        ADD A:100 → current=[A], token=100

Step 2: current=[A], token=100
        A.token + B:250 = 350 < 600 ✓
        ADD B:250 → current=[A,B], token=350

Step 3: current=[A,B], token=350
        A,B.token + C:150 = 500 < 600 ✓
        ADD C:150 → current=[A,B,C], token=500

Step 4: current=[A,B,C], token=500
        A,B,C.token + D:300 = 800 > 600 ✗
        token=500 >= MIN=200? YES
        FLUSH [A,B,C]:500 → CHUNK1
        START NEW [D]:300 ← D alone exceeds min

Step 5: current=[D], token=300
        D.token + E:100 = 400 < 600 ✓
        ADD E:100 → current=[D,E], token=400

Step 6: END OF ATOMICS
        FLUSH [D,E]:400 → CHUNK2

OUTPUT:
  ✓ CHUNK1 [A,B,C]: 500 tokens (within [200,600])
  ✓ CHUNK2 [D,E]: 400 tokens (within [200,600])
```

---

## 4. Multimodal Content Integration

### Image Handling in Chunks

```
CHUNK STRUCTURE:
{
    "id": "document__chunk_12_45",
    "content": {
        "text": "The following diagram shows...",
        "img": ["base64_img_1", "base64_img_2"]  ← Binary data
    },
    "metadata": {
        "images": ["img0_doc_0", "img1_doc_0"],  ← Image IDs for retrieval
        "token_count": 580,                       ← Includes image tokens
        "embeded_content": "...text + descriptions..."
    }
}

RETRIEVAL INDEX:
┌──────────────────────────────────────┐
│ Vector DB (Chroma)                   │
├──────────────────────────────────────┤
│ id: "doc__chunk_12_45_0"             │
│ embedding: [0.123, -0.456, ...]      │
│ document: "The following diagram..." │
│ metadata:                            │
│   images: ["img0_doc_0", "img1_doc_0"]│
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│ PostgreSQL + BM25                    │
├──────────────────────────────────────┤
│ document_id: "doc__chunk_12_45_0"    │
│ search_content: "[SECTION]: ...      │
│  [CONTENT]: The diagram shows...     │
│  [FIGURE_DESCRIPTIONS]               │
│  [0] This diagram depicts a system   │
│  architecture with three components..│
│  [1] A flowchart showing the data    │
│  processing pipeline..."             │
│ text_content: "The following diagram│
│  shows..."                           │
│ metadata: {...}                      │
└──────────────────────────────────────┘

IMAGE LLM DESCRIPTIONS (Generated):
┌──────────────────────────────────────┐
│ img_id: "img0_doc_0"                 │
│ description: "System architecture    │
│  diagram with three interconnected   │
│  components: input layer, processing│
│  layer, output layer. Arrows show    │
│  data flow direction..."             │
└──────────────────────────────────────┘
```

### Token Counting with Images

```
Text tokens: manual_token_count(chunk.text)
Image tokens: len(chunk.images) × IMAGE_TOKEN_ESTIMATE

Example:
  Text: "The system architecture..." → 450 tokens
  Images: 2 images × 300 token/image → 600 tokens
  TOTAL: 1050 tokens

This is included in CHUNK_MAX_TOKEN calculation to avoid
exceeding context window during retrieval.
```

---

## 5. Splitting Strategies Comparison

### When Each Strategy Is Used

```
DOCUMENT CONTENT
├─ Hierarchical Structure (Chapters, Sections)?
│  └─ YES
│     └─ → USE HSF: Respects hierarchy
│        ├─ Node <= MAX?
│        │  └─ YES: Create 1 chunk ✓
│        │  └─ NO: Recurse children or split semantically
│        │
│        └─ Semantic boundaries available?
│           ├─ YES: Split by subheadings
│           │  └─ Each subheading block becomes potential chunk
│           │
│           └─ NO or block still too large
│              └─ FALLBACK: Fixed-size by sentences
│
└─ No clear structure or very long flat text?
   └─ USE FIXED-SIZE: Sentence-level splitting
      └─ Split every N tokens regardless of content

STRATEGY EFFECTIVENESS BY DOCUMENT TYPE:

Medical Paper:
  HSF → ✓ Section by section (Methods, Results, Discussion)

Blog Post (no hierarchy):
  Fixed-size → ✓ Sentence by sentence

Textbook:
  HSF → ✓ Chapter → Section → Subsection flow

Code Documentation:
  HSF → ✓ File → Function → Paragraph structure
```

---

## 6. Edge Case Handling

### Case 1: Very Large Atomic (> MAX_TOKEN)

```
Atomic: Large continuous paragraph, 1500 tokens
Max chunk: 600 tokens

Solution:
  1. Detect: 1500 > 600
  2. Apply fixed_size_split():
     └─ Split by sentences
     └─ Accumulate sentences until token limit reached
  3. Generate multiple chunks from single atomic:
     ├─ [Chunk1: 600 tokens] - sentences 1-15
     ├─ [Chunk2: 600 tokens] - sentences 16-30
     └─ [Chunk3: 300 tokens] - sentences 31-40
  4. All chunks maintain semantic coherence (complete sentences)
```

### Case 2: Chunk Below Minimum (< MIN_TOKEN)

```
Current chunk: 150 tokens (< MIN=200)
Next atomic: 500 tokens (> MAX=600 if combined)

Decision matrix:
├─ Add anyway if next atomic alone < MAX?
│  ├─ YES: Merge + flush (sacrifice minimum)
│  └─ NO: Split next atomic and proceed
└─ Rationale: Incomplete information worse than small chunk

Result: Output [150 + 400] = 550 tokens
        Trade-off: Accept chunk below MIN rather than lose content
```

### Case 3: Document with No Table of Contents

```
PDF has no embedded TOC
Solution:
  1. Fallback: Font size heuristic
     └─ size > 14pt → Heading
     └─ size 10-12pt → Body text
  
  2. Generate pseudo-TOC from font sizes
  
  3. Proceed with normal HSF pipeline
  
  Limitation: May miss semantic structure but still works reasonably
```

---

## 7. Configuration Tuning Guide

### Chunk Size Selection

```
DEFAULT: chunk_max_token=600, chunk_min_token=200

Use case: Dense academic paper → INCREASE MAX
  chunk_max_token: 1000
  └─ Rationale: Semantic units are large, fewer chunks
  └─ Risk: Higher noise in retrieval results

Use case: Long document, many small sections → DECREASE MAX
  chunk_max_token: 300
  └─ Rationale: Finer granularity, more precise retrieval
  └─ Risk: More overhead, potential fragmentation

Use case: Technical documentation → ADJUST MIN
  chunk_min_token: 100  ← Lower minimum
  └─ Rationale: Brief code examples OK
  └─ Risk: May allow orphaned context

Relationship:
  MIN should be ~1/3 of MAX for reasonable distribution
  MIN_TOKEN: ~150-250
  MAX_TOKEN: ~600-1000

Token budget for retrieval:
  token_budget: 2000  ← Total context for LLM
  └─ With 5-7 chunks × 300-400 tokens/chunk = ~1500-2800 tokens
  └─ Leave buffer for prompt and query
```


