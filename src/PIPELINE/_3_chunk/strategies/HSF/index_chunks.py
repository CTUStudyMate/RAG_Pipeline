
import chromadb
# from pipeline_config import EMBEDDING_PROVIDER, FINAL_CHUNKS_TEST_FILEPATH, VECTOR_DB_HSF_PATH
from pipeline_config import settings
from pipeline_setting import PGDBConnectInfo
from src.used_models.embeddings.embed_factory import EmbeddingService 
from pipeline_setup import llm
import psycopg
import json

def embed_content(texts, embedder):
    return embedder.embed(texts)

def get_img_descriptions(current_chunk_imgs):
    system_prompt = """
You are generating image descriptions for a retrieval system.

Return ONLY valid JSON.
Do not include any explanation, markdown, or extra text.

The output must be a JSON array where each item has:
- "img_id": the id of the image (use exactly as provided before each image, do not modify)
- "description": a retrieval-optimized description of the image

Each "description" must be 80–150 words.

Focus on:
- technical concepts
- entities
- diagrams
- tables/charts
- labels and visible text
- UI elements if present
- relationships between components

Include important visible text exactly as written when readable.

Avoid conversational language, speculation, or unnecessary details.

Make descriptions dense with searchable information.
"""

    input_contents = []
    for img in current_chunk_imgs:
        input_contents.append({
            "type": "input_text",
            "text": f"\n\nImage: {img["img_id"]}"
        })
        input_contents.append({
            "type": "input_image",
            "image_url": img["base64"]
        })
        
    response = llm.generate(system_prompt=system_prompt, content=input_contents)
    
    response = json.loads(response) # khúc này có thể cần catch lỗi và retry trong trường hợp invalid json
    
    return response    
        
        

def index_to_pgdb(pgdb_connect_info, chunk_ids, chunk_text_search_contents, chunk_text_contents, chunk_metadatas, cur):
    table_name = pgdb_connect_info.chunks_table

    if not (len(chunk_ids) == len(chunk_text_contents) == len(chunk_metadatas) == len(chunk_text_search_contents)):
        raise ValueError("Input lists must have same length")

    data = [
        (doc_id, search_content, text, json.dumps(meta))
        for doc_id, search_content, text, meta in zip(chunk_ids, chunk_text_search_contents, chunk_text_contents, chunk_metadatas)
    ]

    cur.executemany(
        f"""
        INSERT INTO {table_name} (document_id, search_content, text_content, metadata)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (document_id) DO NOTHING
        """,
        data
    )

    
    
def store_imgs(cur, db_images, pgdb_connect_info:PGDBConnectInfo):
    data = []
    for img_item in db_images:
        data.append((img_item["img_id"], img_item["base64"], img_item["description"]))
    cur.executemany(
        f"""
        INSERT INTO {pgdb_connect_info.images_table} (img_id, base64, description)
        VALUES (%s, %s, %s)
        ON CONFLICT (img_id) DO NOTHING
        """,
        data
    )

def build_index_data(chunks):
    embedder = EmbeddingService(provider=settings.config["embedding_provider"])
    documents = []
    metadatas = []
    ids = []
    
    texts = []
    db_images = []
    
    for i, chunk in enumerate(chunks):
        chunk_text = chunk["content"]["text"]
        chunk_section = chunk["metadata"]["section"]
            
        if chunk_section == " > " or chunk_section == "":
            chunk_section = "General"
        while chunk_section.startswith(" > "):
            chunk_section = chunk_section[3:]
        chunk_section = chunk_section.strip()
        
        store_text = f"[SECTION]: {chunk_section}\n[CONTENT]: {chunk_text}"
        embeded_text = store_text
                 
        documents.append(store_text)
        
        metadata = {
        "document": chunk["metadata"]["document"],
        "section": chunk_section,
        "token_count": chunk["metadata"]["token_count"],
        "chunk_id": chunk["id"],
        "embeded_content": store_text
        }
        
        imgs = chunk["content"]["img"] # này là một mảng các base64
        if imgs:  # chỉ add khi có ảnh
            # metadata["image"] = imgs
            figure_desc_anchor = "\n[FIGURE_DESCRIPTIONS]\n"
            figure_desc_text = ""
            metadata["images"] = []
            current_chunk_imgs = []
            # tạo img_id, lưu từng ảnh vào db
            for img_order, img in enumerate(imgs):
                img_id = f"img{img_order}_{chunk['id']}_{i}"
                # insert img_id, base64 và mô tả vào csdl
                metadata["images"].append(img_id)
                
                current_chunk_imgs.append({
                    "img_id": img_id,
                    "base64": img
                })
            
            img_descriptions = get_img_descriptions(current_chunk_imgs) 
            desc_map = {d["img_id"]: d["description"] for d in img_descriptions} 
            for j,img in enumerate(current_chunk_imgs):
                img["description"] = desc_map.get(img["img_id"], "")
                if img["description"]:
                    figure_desc_text += f"[{j}] {img['description']}\n"
            if figure_desc_text.strip():
                embeded_text += f"{figure_desc_anchor}{figure_desc_text}"
                metadata["embeded_content"] = embeded_text
            db_images.extend(current_chunk_imgs)    
                
        metadatas.append(metadata)
    
        ids.append(f"{chunk['id']}_{i}") # in what cases that this index is needed?
        texts.append(embeded_text)
    
    embeddings = embed_content(texts, embedder)
    
    return ids, embeddings, documents, texts, metadatas, db_images

def get_chroma_collection(collection_name, collection_path=settings.config["vector_db_path"]):
    client = chromadb.PersistentClient(path=collection_path)
    collection = client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})
    return collection, client

def index_to_chroma(collection, ids, embeddings, documents, metadatas, client):
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )
    
    
def index_chunks(collection_name, chunks, pgdb_connect_info):
    ids, embeddings, documents, embeded_texts, metadatas, db_images = build_index_data(chunks)
    
    collection, client = get_chroma_collection(collection_name)
    index_to_chroma(collection=collection, ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas, client=client)   
    
    conn = psycopg.connect(
    host=pgdb_connect_info.host,
    port=pgdb_connect_info.port,
    dbname=pgdb_connect_info.db_name,
    user=pgdb_connect_info.user,
    password=pgdb_connect_info.password,
    options="-c client_encoding=UTF8" # chưa test lại code khi có dòng này
    )
    
    cur = conn.cursor()
    index_to_pgdb(pgdb_connect_info=pgdb_connect_info, chunk_ids=ids, chunk_text_contents=documents, chunk_metadatas=metadatas, chunk_text_search_contents=embeded_texts, cur=cur)
    store_imgs(db_images=db_images, pgdb_connect_info=pgdb_connect_info, cur=cur)
    conn.commit()
    cur.close()
    conn.close()
    
    # debug
    data = []

    for _id, doc, embed, meta in zip(ids, documents, embeded_texts, metadatas):
        data.append({
            "id": _id,
            "document": doc,
            "embeded_content": embed, # trong chroma db thì trường này nhét vào metadata luôn
            "metadata": meta
        })
    with open(settings.config["final_chunks_test_filepath"], "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)