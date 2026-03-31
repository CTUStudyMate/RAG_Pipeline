def print_retrieved_docs(docs, max_text_len=120):
    print("\n" + "="*80)
    print(f"RESULTS ({len(docs)} docs)")
    print("="*80)

    for i, doc in enumerate(docs, start=1):
        doc_id = doc.get("doc_id", "N/A")
        score = doc.get("rrf_score", doc.get("score", 0))
        text = doc.get("text", "")
        metadata = doc.get("metadata", {})

        # truncate text cho gọn
        short_text = text[:max_text_len] + ("..." if len(text) > max_text_len else "")

        print(f"\n[{i}] DOC_ID: {doc_id}")
        print(f"     SCORE : {score:.4f}")
        print(f"     TEXT  : {short_text}")
        print(f"     META  : {metadata}")
        print("-"*80)