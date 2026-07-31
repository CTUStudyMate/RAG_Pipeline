CREATE TABLE hsf_3007_imgs_mini_effort (
  id BIGSERIAL PRIMARY KEY,
  img_id TEXT UNIQUE,
  base64 TEXT NOT NULL,
  description TEXT
);

CREATE TABLE hsf_3007_chunks_mini_effort(
  id BIGSERIAL PRIMARY KEY,
  document_id TEXT UNIQUE,
  search_content TEXT,
  text_content TEXT,
  metadata JSONB
);

create index bm25_on_hsf_3007_chunks_mini_effort on hsf_3007_chunks_mini_effort using bm25(id, search_content) with (key_field='id');