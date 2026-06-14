# HSF Algorithm - Quick Reference & Implementation Guide

## Quick Summary

**HSF (Hierarchical - Semantic - FixedSize)** is a document chunking algorithm that:

1. **Preserves hierarchy** - Respects document structure (chapters → sections → subsections)
2. **Semantic splitting** - Groups content by logical boundaries (headings, paragraphs)
3. **Handles multimodal** - Supports text, images, and tables as atomic units
4. **Token-compliant** - Guarantees all chunks fit within [MIN_TOKEN, MAX_TOKEN]
5. **Graceful fallback** - Uses fixed-size splitting for oversized content

---

## Core Algorithm in 50 Lines

```python
def build_chunks(node, max_token=600):
    """
    Recursively chunk a document hierarchy.
    
    Strategy:
    1. If node fits in one chunk → done
    2. If node too large but has children → recurse into children
    3. If node too large and is leaf → split using semantic + fixed-size
    """
    if node.token_count <= max_token:
        # CASE 1: Node fits
        return create_chunk(node)
    
    elif node.children:
        # CASE 2: Recurse into children
        chunks = []
        for child in node.children:
            chunks.extend(build_chunks(child, max_token))
        return chunks
    
    else:
        # CASE 3: Leaf too large - split by semantics then fixed-size
        atomics = load_atomics(node)
        blocks = split_by_subheadings(atomics)
        chunks = []
        
        for block in blocks:
            if sum(a.token for a in block) <= max_token:
                chunks.append(create_chunk_from_atomics(block))
            else:
                # Fallback: greedy semantic units
                chunks.extend(chunk_by_semantic_units(block, max_token))
        
        return chunks


def chunk_by_semantic_units(atomics, max_token, min_token=200):
    """
    Greedily accumulate atomics into chunks.
    
    Core logic:
    - Add atomic to current chunk if it fits
    - When adding would exceed max:
      * If current >= min: flush and start new
      * Else: add anyway (sacrifice min) or split atomic
    """
    chunks = []
    current_chunk = []
    current_token = 0
    
    for atomic in atomics:
        if current_token + atomic.token > max_token:
            # Would exceed limit
            if current_token >= min_token:
                # Current chunk good enough → flush
                chunks.append(current_chunk)
                current_chunk = []
                current_token = 0
            elif atomic.token < max_token:
                # Atomic alone fits → add anyway and flush
                current_chunk.append(atomic)
                chunks.append(current_chunk)
                current_chunk = []
                current_token = 0
                continue
            else:
                # Atomic > max → split it
                split_parts = fixed_size_split(atomic, max_token)
                current_chunk.append(split_parts[0])
                chunks.append(current_chunk)
                chunks.extend(split_parts[1:])
                current_chunk = []
                current_token = 0
                continue
        
        current_chunk.append(atomic)
        current_token += atomic.token
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks
```

---

## Configuration Quick Start

```yaml
# RECOMMENDED DEFAULTS (for academic papers)
chunk_max_token: 600          # Max size per chunk
chunk_min_token: 200          # Min size (soft constraint)
image_token_estimate: 300     # Estimated tokens/image
token_budget: 2000            # Total context window

# ADJUST FOR YOUR USE CASE
# Dense academic: chunk_max=1000, chunk_min=250
# Short docs: chunk_max=300, chunk_min=50
# Mixed media: chunk_max=600, image_token=400
```

---

## Implementation Checklist

- [x] **Phase 1**: Extract atomics from PDF (Docling)
- [x] **Phase 2**: Build hierarchy tree from TOC
- [x] **Phase 3**: Associate atomics to hierarchy nodes
- [x] **Phase 4**: Compute token counts recursively
- [x] **Phase 5**: Apply build_chunks() recursively
- [x] **Phase 6**: Generate image descriptions (LLM)
- [x] **Phase 7**: Index in vector DB + PostgreSQL

**Source Code Location:**
```
src/PIPELINE/_3_chunk/strategies/HSF/
├─ HSF_chunking.py           ← Entry point
├─ process_chunks.py         ← Core chunking logic
├─ process_token.py          ← Token computation
├─ process_atomics.py        ← Atomic extraction
├─ hierarchy_helpers/        ← TOC parsing
└─ atomic_db_helpers/        ← SQLite management
```

---

## Common Issues & Solutions

### Issue 1: Chunks Exceed MAX_TOKEN

**Symptom**: Some output chunks > 600 tokens

**Root Cause**: Very large atomic element OR bug in fixed-size split

**Solution**:
```python
# Check: Add debugging to detect oversized atomics
if chunk.token_count > CHUNK_MAX_TOKEN:
    print(f"ERROR: Chunk {chunk.id} exceeds max: {chunk.token_count}")
    # Should never happen with proper HSF implementation
```

### Issue 2: Semantic Split Not Working

**Symptom**: Chunks break mid-sentence or within tables

**Root Cause**: `is_text_incomplete()` not detecting incomplete sentences

**Solution**:
```python
# Improve sentence boundary detection
def is_text_incomplete(text: str) -> bool:
    """
    Check if text ends with incomplete sentence.
    Returns True if should continue accumulating.
    """
    text = text.strip()
    if not text:
        return False
    
    # Text incomplete if:
    # - Ends with comma (list continuation)
    # - Ends with "(" or "[" (opening bracket)
    # - Last sentence doesn't end with . ! ? 
    ends_with = text[-1]
    return ends_with in (',', '(', '[', ';')
```

### Issue 3: Images Lose Reference

**Symptom**: Image stored but not retrievable from chunk

**Root Cause**: Image ID not preserved through chunking process

**Solution**:
```python
# Track image IDs through chunking pipeline
chunk["metadata"]["images"] = []  # List of img_ids

# When merging atomics:
if atomic.type == "picture":
    img_id = generate_img_id(chunk.id, atomic.order)
    chunk["metadata"]["images"].append(img_id)
    # Store image separately in DB
    db.store_image(img_id, atomic.base64, description)
```

### Issue 4: Token Count Mismatch

**Symptom**: `sum(atomics.tokens) != node.token_count`

**Root Cause**: Image token estimation or double-counting

**Solution**:
```python
# Recompute token count carefully
def compute_chunk_tokens(chunk):
    text_tokens = manual_token_count(chunk["content"]["text"])
    image_tokens = len(chunk["content"]["img"]) * IMAGE_TOKEN_ESTIMATE
    return text_tokens + image_tokens

# Validate:
assert chunk["metadata"]["token_count"] == compute_chunk_tokens(chunk)
```

---

## Debugging Tips

### Enable Logging

```python
# In process_chunks.py, add logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug(f"Node {node.title}: {node.token_count} tokens")
logger.debug(f"  Split into {len(blocks)} blocks")
logger.debug(f"  Generated {len(chunks)} chunks")
```

### Visualize Hierarchy

```python
def print_tree(node, indent=0):
    """Print hierarchy tree with token counts"""
    prefix = "  " * indent
    token_str = f"[{node.token_count} tokens]" if hasattr(node, 'token_count') else ""
    print(f"{prefix}├─ {node.title} {token_str}")
    for child in node.get("children", []):
        print_tree(child, indent + 1)

print_tree(hierarchy_tree)
```

### Inspect Chunks

```python
def inspect_chunks(chunks):
    """Print chunk statistics"""
    print(f"Total chunks: {len(chunks)}")
    tokens = [c["metadata"]["token_count"] for c in chunks]
    print(f"Token range: {min(tokens)} - {max(tokens)}")
    print(f"Average: {sum(tokens) / len(tokens):.1f}")
    
    # Find problematic chunks
    oversized = [c for c in chunks if c["metadata"]["token_count"] > 600]
    undersized = [c for c in chunks if c["metadata"]["token_count"] < 200]
    print(f"Oversized: {len(oversized)}, Undersized: {len(undersized)}")
```

---

## Performance Optimization

### Bottleneck 1: LLM Image Descriptions

**Problem**: Generating descriptions for every image is slow

**Solution**: Batch images, cache descriptions

```python
# Instead of: FOR EACH image → call LLM
# Do: BATCH multiple images → single LLM call

def get_batch_descriptions(images, batch_size=10):
    """Batch LLM calls for multiple images"""
    for i in range(0, len(images), batch_size):
        batch = images[i:i+batch_size]
        descriptions = llm.generate_descriptions_batch(batch)
        yield from descriptions
```

### Bottleneck 2: Token Computation

**Problem**: Recomputing tokens on every merge

**Solution**: Cache and update incrementally

```python
# Don't: recompute every time
# current_tokens = manual_token_count(chunk["content"]["text"])

# Do: Update incrementally
def merge_atomic_with_cache(chunk, atomic):
    chunk["content"]["text"] += atomic.content
    chunk["metadata"]["token_count"] += atomic.token  # ← No recomputation
```

### Bottleneck 3: Database Queries

**Problem**: Fetching atomics one-by-one in loop

**Solution**: Batch fetch

```python
# Don't: FOR EACH node, query database
# Do: Batch load all atomics upfront

def load_all_atomics(hierarchy_tree):
    """Load all atomics in single query"""
    all_ids = collect_all_gold_units(hierarchy_tree)
    return db.query("SELECT * FROM atomics WHERE id IN (?)", all_ids)
```

---

## Testing Strategy

### Test 1: Token Compliance

```python
def test_chunk_tokens():
    """Verify all chunks respect token bounds"""
    chunks = hsf_chunk(test_pdf)
    
    for chunk in chunks:
        tokens = chunk["metadata"]["token_count"]
        assert 0 < tokens <= 600, f"Chunk {chunk['id']}: {tokens} tokens"
        assert tokens >= 200 or len(chunks) == 1, f"Too small: {tokens}"  # Allow single small chunk
```

### Test 2: No Data Loss

```python
def test_completeness():
    """Verify no content lost during chunking"""
    doc_text = extract_text(input_pdf)
    chunks = hsf_chunk(input_pdf)
    
    chunk_text = "".join(c["content"]["text"] for c in chunks)
    
    # Check: all original content in chunks (ignoring formatting)
    doc_words = set(doc_text.split())
    chunk_words = set(chunk_text.split())
    
    assert chunk_words >= doc_words, "Content lost during chunking"
```

### Test 3: Semantic Boundaries

```python
def test_semantic_integrity():
    """Verify semantic units not broken"""
    chunks = hsf_chunk(test_pdf)
    
    for chunk in chunks:
        # Check: chunk text doesn't end mid-sentence
        text = chunk["content"]["text"].strip()
        last_char = text[-1] if text else ""
        
        # Should end with sentence terminator or heading
        assert last_char in ".:!?#", f"Broken boundary: '{text[-20:]}'"
```

---

## Quick Comparison: HSF vs Alternatives

```
                    HSF          Fixed-Size    Recursive
Hierarchy           ✓ Preserved  ✗ Lost        ✗ Lost
Structure-aware     ✓ Yes        ✗ No          ~ Partial
Token guarantee     ✓ Yes        ✓ Yes         ✗ Heuristic
Multimodal          ✓ Native     ✗ Breaks      ✗ Breaks
Edge case handling  ✓ Graceful   ✓ Simple      ✗ Problematic
Retrieval quality   ⭐⭐⭐⭐⭐   ⭐⭐⭐       ⭐⭐⭐⭐
Implementation      ~ Moderate   ✓ Simple      ~ Moderate
```

---

## When NOT to Use HSF

❌ **Use Fixed-Size Instead If:**
- Document has no clear hierarchy (e.g., unstructured notes)
- Speed is critical and LLM calls unacceptable
- Simple token-based splitting sufficient

❌ **Use Recursive Splitter Instead If:**
- Document is flat narrative text
- Need maximum semantic awareness for chunking
- Willing to accept slower processing

✅ **Use HSF If:**
- Document has hierarchy (academic papers, reports, textbooks)
- Quality matters more than speed
- Multimodal content present
- Token compliance critical

---

## Further Reading

- **Docling**: PDF parsing library → https://github.com/DS4SD/docling
- **ChromaDB**: Vector database → https://www.trychroma.com/
- **ParadeDB**: PostgreSQL with BM25 → https://paradedb.com/
- **Token Counting**: OpenAI tiktoken → https://github.com/openai/tiktoken

---

## Quick Links (in this repo)

- **Full Algorithm Doc**: `docs/HSF_ALGORITHM.md`
- **Visual Guides**: `docs/HSF_VISUAL_GUIDE.md`
- **Source Code**: `src/PIPELINE/_3_chunk/strategies/HSF/`
- **Config**: `EXPERIMENTS/chunk_versions/hsf_*/config.yaml`

