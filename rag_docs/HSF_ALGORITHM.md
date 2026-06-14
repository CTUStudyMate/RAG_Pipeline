# HSF (Hierarchical - Semantic - FixedSize) Chunking Algorithm

## Overview

HSF is a novel document chunking algorithm that preserves document hierarchy, semantic boundaries, and multimodal content while maintaining strict token constraints. It is designed for large, structured documents with hierarchical organization (e.g., academic papers, technical reports, textbooks).

**Key Characteristics:**
- **Hierarchical Preservation**: Respects document structure (chapters → sections → subsections)
- **Semantic Awareness**: Groups content by semantic boundaries (headings, paragraphs)
- **Multimodal Support**: Preserves text, images, tables as atomic units
- **Token Budget Compliance**: All chunks fit within `[CHUNK_MIN_TOKEN, CHUNK_MAX_TOKEN]`
- **Fallback Handling**: Gracefully handles outliers (very large atomics or sections)

---

## Algorithm Pipeline

The HSF algorithm consists of 7 main phases:

```
Phase 1: Parse PDF → Phase 2: Build Hierarchy → Phase 3: Extract Atomics
         ↓                      ↓                       ↓
Phase 4: Compute Tokens → Phase 5: Recursively Chunk → Phase 6: Generate Descriptions
         ↓                                             ↓
Phase 7: Index & Store (Vector DB + PostgreSQL)
```

---

## Phase 1: Parse PDF into Atomic Elements

**Goal**: Extract basic content units (text, images, tables) with document order preserved.

### Input
- PDF file path

### Output
- SQLite database with atomic elements (gold_units)
- Each atomic has: id, content, type, token_count, atomic_order

### Pseudocode

```
FUNCTION parse_pdf_into_atomic_units(pdf_path):
    // Step 1: Initialize
    batches = split_pdf_into_batches(pdf_path)  // Use Docling for PDF parsing
    hierarchy_tree = build_hierarchy(pdf_path)
    atomic_db = create_sqlite_db(pdf_path)
    atomic_order = 0
    
    // Step 2: Process each batch
    FOR EACH batch IN batches:
        docling_doc = parse_batch(batch)          // Docling extracts structured content
        flat_elements = flatten_document(docling_doc)
        
        FOR EACH element IN flat_elements:
            // Extract atomic information
            IF element is TEXT:
                content = element.text
                type = "text"
                is_incomplete = is_text_incomplete(content)
                
            ELSE IF element is PICTURE:
                content = element.base64_image
                type = "picture"
                
            ELSE IF element is SECTION_HEADER:
                content = element.heading_text
                type = "section_header"
                heading_type = determine_heading_type(element)
            
            ELSE IF element is TABLE:
                content = element.markdown_table
                type = "table"
            
            token_count = compute_token_count(content)
            
            // Associate with hierarchy node
            hierarchy_node = find_node_for_element(hierarchy_tree, element)
            hierarchy_node.gold_units.append(atomic_id)
            
            // Store in database
            INSERT INTO atomic_elements 
            VALUES (atomic_id, content, type, token_count, atomic_order)
            
            atomic_order += 1
    
    RETURN (atomic_db, hierarchy_tree)
```

**Key Implementation Details:**
- Docling (document parsing library) extracts structured content
- Flatten operation unwraps grouped elements recursively
- Text completeness check: Does text end with period/complete sentence?
- Hierarchy node association: Match element position with document outline

---

## Phase 2: Build Document Hierarchy

**Goal**: Create a tree structure that respects document outline (TOC) and heading levels.

### Input
- PDF file path

### Output
- Hierarchy tree: `{level, title, children, page, [token_count], [gold_units]}`

### Pseudocode

```
FUNCTION build_hierarchy(pdf_path):
    doc = open_pdf(pdf_path)
    toc = extract_table_of_contents(doc)  // Extract PDF TOC
    
    // If no TOC, use heuristic: font size > 14pt = heading
    IF toc is empty:
        toc = generate_smart_toc_from_fonts(doc)
    
    hierarchy_tree = build_tree_from_toc(toc)
    
    RETURN hierarchy_tree

FUNCTION build_tree_from_toc(toc_entries):
    // toc_entries = [(level, title, page), ...]
    root = create_node(level=0, title="ROOT", page=0)
    node_stack = [root]
    
    FOR EACH (level, title, page) IN toc_entries:
        new_node = create_node(level, title, page)
        new_node.children = []
        
        // Pop nodes until stack top has lower level
        WHILE node_stack.length > 0 AND node_stack.top.level >= level:
            node_stack.pop()
        
        // Attach to current top as child
        node_stack.top.children.append(new_node)
        node_stack.push(new_node)
    
    RETURN root

NODE STRUCTURE:
{
    "level": int,                    // 0=root, 1=chapter, 2=section
    "title": string,                 // Normalized heading text
    "page": int,                     // Start page in PDF
    "children": [Node, ...],         // Child nodes
    "metadata": {
        "description": string,       // Full heading path
        "[token_count]": int,        // Computed later
        "[gold_unit]": [ids]         // Associated atomic elements
    }
}
```

---

## Phase 3: Associate Atomics with Hierarchy

**Goal**: Link each atomic element to its hierarchy node.

### Pseudocode

```
FUNCTION associate_atomics_to_hierarchy(atomics_db, hierarchy_tree):
    cursor = atomics_db.cursor()
    cursor.execute("SELECT * FROM atomic_elements ORDER BY atomic_order")
    
    passed_cursor = DFSCursor(hierarchy_tree)
    current_open_node = passed_cursor.next()  // Start at ROOT
    
    FOR EACH atomic IN cursor.fetchall():
        element_page = extract_page_from_element(atomic)
        element_type = atomic.type
        
        // Determine which hierarchy node this atomic belongs to
        IF element_type == "section_header":
            // Match heading to hierarchy node by text similarity
            matching_node = find_hierarchy_node_by_heading(element_text, hierarchy_tree)
            IF matching_node found:
                current_open_node = matching_node
        
        // Associate atomic with current open node
        current_open_node.gold_units.append(atomic.id)
```

---

## Phase 4: Compute Token Count for Hierarchy

**Goal**: Calculate token count for each hierarchy node (includes all descendants).

### Input
- Hierarchy tree with associated atomics
- Atomic elements database

### Output
- Updated hierarchy tree with `token_count` field for each node

### Pseudocode

```
FUNCTION compute_tree_token(hierarchy_tree, atomics_db):
    cursor = atomics_db.cursor()
    cursor.execute("SELECT id, token_count FROM atomic_elements")
    token_map = dict(cursor.fetchall())  // {atomic_id: token_count}
    
    total_tokens = compute_node_token(hierarchy_tree, token_map)
    RETURN total_tokens

FUNCTION compute_node_token(node, token_map):
    // Sum tokens of all gold_units (atomics) in this node
    node_token = 0
    FOR EACH gold_unit_id IN node.gold_units:
        node_token += token_map.get(gold_unit_id, 0)
    
    // Recursively add tokens from all children
    FOR EACH child IN node.children:
        node_token += compute_node_token(child, token_map)
    
    node.token_count = node_token
    RETURN node_token
```

---

## Phase 5: Hierarchical Chunking (Main Algorithm)

**Goal**: Recursively partition the hierarchy into chunks that satisfy token constraints.

### Input
- Hierarchy tree with computed token counts
- Atomics database
- Config: `CHUNK_MAX_TOKEN`, `CHUNK_MIN_TOKEN`, `IMAGE_TOKEN_ESTIMATE`

### Output
- List of chunks: `{id, content: {text, img}, metadata: {section, token_count, document}}`

### Core Algorithm: `build_chunks()`

```
FUNCTION build_chunks(node, file_path, atomics_db, prefix_path=""):
    """
    Recursively chunks a hierarchy node.
    
    Strategy:
    1. If node token < MAX: create chunk from node
    2. If node token >= MAX but has children: recurse into children
    3. If node is leaf & token >= MAX: split node using semantic + fixed-size
    """
    
    // BASE CASE: Node fits in single chunk
    IF node.token_count <= CHUNK_MAX_TOKEN:
        RETURN create_chunk(node, atomics_db, file_path, prefix_path)
    
    // RECURSIVE CASE 1: Node too large but has children
    ELSE IF node.children is not empty:
        chunks = []
        FOR EACH child IN node.children:
            chunks.extend(build_chunks(child, file_path, atomics_db, prefix_path))
        RETURN chunks
    
    // RECURSIVE CASE 2: Leaf node too large
    ELSE:
        RETURN create_chunk(node, atomics_db, file_path, prefix_path)
```

### Sub-function: `create_chunk()`

```
FUNCTION create_chunk(node, atomics_db, file_path, prefix_path):
    """
    Create chunk(s) from a single hierarchy node.
    """
    
    // Load all atomics for this node
    atomics = load_atomics_for_node(node, atomics_db)
    
    IF node.token_count == 0:
        RETURN []
    
    // CASE 1: Node fits in single chunk
    IF node.token_count <= CHUNK_MAX_TOKEN:
        chunk = chunk_from_atomics(atomics, node.token_count, 
                                   node.metadata.description, file_path)
        RETURN [chunk]
    
    // CASE 2: Node too large - split by semantic boundaries
    blocks = split_atomics_by_subheadings(atomics)
    
    chunks = []
    FOR EACH block IN blocks:
        block_token = sum(atomic.token_count FOR atomic IN block)
        block_heading = block[0].content
        block_path = node.metadata.description + " > " + block_heading
        
        IF block_token <= CHUNK_MAX_TOKEN:
            chunk = chunk_from_atomics(block, block_token, block_path, file_path)
            chunks.append(chunk)
        ELSE:
            // Block still too large: apply fixed-size semantic chunking
            block_chunks = chunk_by_semantic_units(
                atomics = block,
                max_token = CHUNK_MAX_TOKEN,
                min_token = CHUNK_MIN_TOKEN,
                section_path = block_path,
                file_path = file_path
            )
            chunks.extend(block_chunks)
    
    RETURN chunks
```

### Sub-function: `chunk_by_semantic_units()` - Greedy Semantic Grouping

```
FUNCTION chunk_by_semantic_units(atomics, max_token, min_token, 
                                  section_path, file_path):
    """
    Greedily group atomics into chunks respecting token constraints.
    
    Core idea:
    - Accumulate atomics into current chunk
    - When adding next atomic would exceed MAX:
      * If current chunk >= MIN: flush it, start fresh
      * Else: try to add anyway, or split the atomic
    """
    
    chunks = []
    current_chunk = create_empty_chunk(section_path)
    first_atomic_id = None
    
    FOR EACH atomic IN atomics:
        current_token = current_chunk.metadata.token_count
        atomic_token = atomic.token_count
        
        IF first_atomic_id is None:
            first_atomic_id = atomic.atomic_order
        
        // Check if adding this atomic would exceed limit
        IF current_token + atomic_token >= max_token:
            
            // DECISION 1: Current chunk meets minimum
            IF current_token >= min_token:
                // Flush current chunk
                flush_chunk(current_chunk, chunks, first_atomic_id)
                current_chunk = create_empty_chunk(section_path)
                first_atomic_id = None
                
                merge_atomic_to_chunk(current_chunk, atomic)
                CONTINUE
            
            // DECISION 2: Current chunk below minimum
            ELSE:
                // Try to add atomic if it's not too large
                IF atomic_token < max_token:
                    merge_atomic_to_chunk(current_chunk, atomic)
                    flush_chunk(current_chunk, chunks, first_atomic_id)
                    current_chunk = create_empty_chunk(section_path)
                    first_atomic_id = None
                    CONTINUE
                
                // DECISION 3: Atomic too large (> max_token)
                // Split it and merge first part with current chunk
                ELSE:
                    split_chunks = fixed_size_split(atomic, file_path,
                                                   max_token - current_token,
                                                   section_path)
                    
                    merged = merge_chunk_to_chunk(current_chunk, split_chunks[0])
                    flush_chunk(merged, chunks, first_atomic_id)
                    chunks.extend(split_chunks[1:])
                    
                    current_chunk = create_empty_chunk(section_path)
                    first_atomic_id = None
                    CONTINUE
        
        // Atomic fits: add to current chunk
        merge_atomic_to_chunk(current_chunk, atomic)
    
    // Flush any remaining content
    IF current_chunk.token_count > 0:
        flush_chunk(current_chunk, chunks, first_atomic_id)
    
    RETURN chunks
```

### Sub-function: `merge_atomic_to_chunk()`

```
FUNCTION merge_atomic_to_chunk(chunk, atomic):
    """
    Intelligently merge an atomic element into a chunk.
    """
    
    is_incomplete = chunk.metadata.get("is_incomplete_text", FALSE)
    chunk_text = chunk.content.text or ""
    
    IF atomic.type == "text":
        text = atomic.content
        
        // Handle incomplete sentences from previous atomic
        IF is_incomplete:
            chunk_text += " " + text
        ELSE:
            chunk_text += "\n" + text IF chunk_text ELSE text
        
        is_incomplete = is_text_incomplete(text)
    
    ELSE IF atomic.type == "section_header":
        IF chunk_text.strip() is empty:
            RETURN chunk  // Skip if chunk empty (avoid duplicate heading)
        
        text = atomic.content
        IF atomic.heading_type == "main":
            chunk_text += "\n\n# " + atomic.description
        ELSE:
            chunk_text += "\n\n" + text
        
        is_incomplete = FALSE
    
    ELSE IF atomic.type == "picture":
        chunk.content.images.append(atomic.content)  // base64
    
    ELSE IF atomic.type == "table":
        chunk_text += "\n" + atomic.content + "\n"
        is_incomplete = FALSE
    
    // Update chunk state
    chunk.content.text = chunk_text
    chunk.metadata.is_incomplete_text = is_incomplete
    
    // Recompute token count
    text_tokens = manual_token_count(chunk_text)
    image_tokens = len(chunk.images) * IMAGE_TOKEN_ESTIMATE
    chunk.metadata.token_count = text_tokens + image_tokens
    
    RETURN chunk
```

### Sub-function: `fixed_size_split()` - Fallback for Outliers

```
FUNCTION fixed_size_split(atomic, file_path, target_token, section_path):
    """
    Split an oversized atomic using sentence-based tokenization.
    Fallback when semantic boundaries insufficient.
    """
    
    IF atomic.type != "text":
        RETURN [atomic]  // Don't split images, tables
    
    text = atomic.content
    sentences = split_into_sentences(text)
    chunks = []
    current_text = ""
    current_tokens = 0
    chunk_count = 0
    
    FOR EACH sentence IN sentences:
        sentence_tokens = token_count(sentence)
        
        IF current_tokens + sentence_tokens > target_token AND current_text not empty:
            // Flush current chunk
            chunk_obj = chunk_from_atomics(
                [create_atomic(current_text, "text", current_tokens)],
                current_tokens, section_path, file_path
            )
            chunks.append(chunk_obj)
            current_text = ""
            current_tokens = 0
        
        current_text += sentence + " "
        current_tokens += sentence_tokens
    
    // Flush remaining
    IF current_text not empty:
        chunk_obj = chunk_from_atomics(
            [create_atomic(current_text, "text", current_tokens)],
            current_tokens, section_path, file_path
        )
        chunks.append(chunk_obj)
    
    RETURN chunks
```

---

## Phase 6: Generate Image Descriptions

**Goal**: Create dense, retrieval-optimized descriptions for images using LLM.

### Pseudocode

```
FUNCTION get_image_descriptions(chunk_images, llm):
    """
    For each image in chunk, generate retrieval-optimized description.
    Descriptions indexed for hybrid search with text.
    """
    
    system_prompt = """
    Generate image descriptions for retrieval system.
    Focus on: technical concepts, entities, diagrams, 
    tables, visible text, labels, relationships.
    Return JSON: [{img_id, description}, ...]
    Each description: 80-150 words, dense with searchable terms.
    """
    
    image_contents = []
    FOR EACH image IN chunk_images:
        image_contents.append({
            "type": "text",
            "text": "\n\nImage: " + image.img_id
        })
        image_contents.append({
            "type": "image_url",
            "image_url": image.base64
        })
    
    response = llm.generate(
        system_prompt = system_prompt,
        content = image_contents
    )
    
    descriptions = json.parse(response)
    RETURN descriptions  // [{img_id, description}, ...]
```

---

## Phase 7: Index and Store

**Goal**: Store chunks in vector DB and relational DB for retrieval.

### Pseudocode

```
FUNCTION index_chunks(chunks, vectordb_config, pgdb_config):
    
    embedder = create_embedder(vectordb_config.embedding_provider)
    
    FOR EACH chunk IN chunks:
        // Step 1: Build search content (text + metadata + descriptions)
        chunk_text = chunk.content.text
        section = chunk.metadata.section
        embedded_content = "[SECTION]: " + section + "\n[CONTENT]: " + chunk_text
        
        // Step 2: Generate embedding
        embedding = embedder.embed(embedded_content)
        
        // Step 3: Add image descriptions to embedded content
        IF chunk.images not empty:
            descriptions = get_image_descriptions(chunk.images, llm)
            embedded_content += "\n[FIGURE_DESCRIPTIONS]\n"
            desc_map = {d.img_id: d.description FOR d IN descriptions}
            
            FOR EACH image IN chunk.images:
                IF image.img_id IN desc_map:
                    embedded_content += desc_map[image.img_id] + "\n"
        
        // Step 4: Store in vector DB (Chroma)
        vectordb.add(
            ids = [chunk.id],
            embeddings = [embedding],
            documents = [chunk.content.text],
            metadatas = [{
                "document": chunk.metadata.document,
                "section": chunk.metadata.section,
                "token_count": chunk.metadata.token_count,
                "images": chunk.metadata.images
            }]
        )
        
        // Step 5: Store in PostgreSQL with BM25 index
        pgdb.execute("""
            INSERT INTO chunks 
            (document_id, search_content, text_content, metadata)
            VALUES (?, ?, ?, ?)
        """, [
            chunk.id,
            embedded_content,        // For BM25 search
            chunk.content.text,      // Display text
            json.dump(chunk.metadata)
        ])
        
        // Step 6: Store images separately
        FOR EACH image IN chunk.images:
            description = get_description_for_image(image.img_id, descriptions)
            pgdb.execute("""
                INSERT INTO images (img_id, base64, description)
                VALUES (?, ?, ?)
            """, [image.img_id, image.base64, description])

RETURN chunks
```

---

## Configuration Parameters

```yaml
# Chunking constraints (tunable)
chunk_max_token: 600          # Maximum tokens per chunk
chunk_min_token: 200          # Minimum tokens per chunk (soft constraint)

# Resource estimation
image_token_estimate: 300     # Estimated tokens per image
token_budget: 2000            # Max tokens for retrieval context window

# Retrieval thresholds
cosine_similarity_threshold: 0.4  # Filter low-confidence vector results
rrf_ranking_constant: 60          # Reciprocal rank fusion constant
```

---

## Complexity Analysis

Let `N` = total tokens in document, `M` = max chunk size, `H` = hierarchy depth

| Phase | Time | Space |
|-------|------|-------|
| Parse PDF | O(N) | O(N) |
| Build Hierarchy | O(pages) | O(H) |
| Compute Tokens | O(N) | O(N) |
| **Chunk (Main Loop)** | **O(N)** | **O(N)** |
| Index | O(chunks) | O(chunks) |
| **Total** | **O(N)** | **O(N)** |

Linear in document size - no expensive operations.

---

## Advantages Over Fixed-Size & Recursive Chunking

| Aspect | Fixed-Size | Recursive | **HSF** |
|--------|-----------|-----------|---------|
| Structure | ❌ Lost | ✓ Kept | ✓ **Kept** |
| Semantic boundaries | ❌ No | ✓ Yes | ✓ **Yes** |
| Images/Tables | ❌ Broken | ❌ Broken | ✓ **Preserved** |
| Token compliance | ✓ Yes | ✓ Yes | ✓ **Yes** |
| Semantic splitting | ❌ No | ❌ No | ✓ **Yes** |
| Multimodal | ❌ No | ❌ No | ✓ **Yes** |

---

## Edge Cases & Handling

| Edge Case | Solution |
|-----------|----------|
| Section > MAX_TOKEN | Split by subheadings, then fixed-size if needed |
| Single atomic > MAX_TOKEN | Sentence-level fixed-size split |
| Empty section | Skip (token_count = 0) |
| Very large heading | Skip from search index (length > 300) |
| No document TOC | Font-size heuristic as fallback |
| Image without description | Graceful degrade (no description stored) |
| Incomplete text segment | Merge with next atomic to maintain context |

---

## Example Walkthrough

**Input Document:**
```
Chapter 1: Introduction (token=5000)
├── Section 1.1: Background (token=2000)
├── Section 1.2: Motivation (token=2000)
└── Section 1.3: Contributions (token=1000)

Config: MAX=600, MIN=200
```

**Execution:**

```
1. build_chunks(Chapter1[5000]):
   - 5000 > 600, has children
   - Recurse: build_chunks(Section 1.1[2000])
   
2. build_chunks(Section 1.1[2000]):
   - 2000 > 600, no children
   - create_chunk(Section 1.1[2000])
   
3. create_chunk(Section 1.1[2000]):
   - Split by subheadings (nottoc):
     * Block 1 [650 tokens] -> Exceeds MAX
     * Block 2 [750 tokens] -> Exceeds MAX
   
4. chunk_by_semantic_units([atomics], 600):
   - Accumulate atomics:
     * Atomic 1-4: 580 tokens < 600 ✓ flush
     * Atomic 5-8: 610 tokens > 600
       - Current 0 < MIN(200): add anyway + split atomic 8
   
Output chunks:
├── Chunk 1: [580 tokens] "Section 1.1 background..."
├── Chunk 2: [480 tokens] + Chunk 3: [200 tokens] from split
└── (Repeat for sections 1.2, 1.3)
```

---

## Future Enhancements

1. **Semantic Similarity Merging**: Combine small chunks with similar content
2. **Query-Adaptive Chunking**: Adjust token limits based on query complexity
3. **Citation-Aware**: Keep citations together with cited content
4. **Multi-Language**: Language-specific sentence splitting
5. **Domain-Specific Parsing**: Medical/legal document templates

---

## References

- Docling: Structured Document Parsing Library
- ChromaDB: Vector Database for Embeddings
- ParadeDB: PostgreSQL with BM25 Full-Text Search
- Token Counting: BPE encoding (OpenAI tiktoken compatible)

