CREATE TABLE hsf_600_seperate_img_160526_imgs (
  id BIGSERIAL PRIMARY KEY,
  img_id TEXT UNIQUE,
  base64 TEXT NOT NULL,
  description TEXT
);

CREATE TABLE hsf_600_seperate_img_160526_chunks(
  id BIGSERIAL PRIMARY KEY,
  document_id TEXT UNIQUE,
  search_content TEXT,
  text_content TEXT,
  metadata JSONB
);

create index bm25_on_hsf_600_seperate_img_160526_chunks on hsf_600_seperate_img_160526_chunks using bm25(id, search_content) with (key_field='id');