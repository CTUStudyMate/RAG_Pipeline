(Nếu đổi tài liệu để parse, đổi file parse: đổi đường dẫn file pdf trong _1_ingest -> ingest.py)

### CONFIG:
Config trong project:
    - file pipeline_config: file config tổng quát, file này sẽ trỏ tới file config chứa tên các llm, provider, embed model... đang được sử dụng.
    
    - mỗi thực nghiệm có config riêng (chủ yếu do khác nhau ở lựa chọn model, provider, bảng lưu riêng trong csdl..), nên sẽ có file config riêng cho từng thực nghiệm nằm ngay trong chính thư mục thực nghiệm đó. Vd thư mục hsf_bge có file config.yaml có embed_model=bge-m3-latest, provider=pge,... 
    
    - pipeline_config.py đang trỏ tới file config nào thì các set up trong file đó sẽ được dùng cho toàn bộ quá trình chunk+retrieve+generate. Vì vậy, mỗi thực nghiệm khác nhau cần kiểm tra xem pipeline_config có đang trỏ đúng tới file config cho thực nghiệm không.


# CHUNK
1. Tạo thư mục thực nghiệm mới trong EXPERIMENTS.chunk_versions (copy hsf_bge) 
    => sửa tên thư mục thực nghiệm 
    => xóa hết dữ liệu trong debug_data và vectorchunks_storage nếu copy từ thư mục cũ qua
2. Trong pipeline_config.py sửa file config thành file config trong thư mục thực nghiệm mới
    vd  config_path="./EXPERIMENTS/chunk_versions/hsf_vi/config.yaml" => config_path="./EXPERIMENTS/chunk_versions/hsf_bge/config.yaml"
3. Trong file config.yaml của thư mục thực nghiệm mới, sửa các phần sau:
        + dòng đầu tiên: chunk_config: "./EXPERIMENTS/chunk_versions/hsf_bge/config.yaml"  hsf_bge sửa thành tên thư mục thực nghiệm (tức là trỏ tới đúng vị trí của file config này)
        + ####### store and debug ################## (xem các kết quả chạy)

        + pgdb:
                chunks_table: "hsf_bge_chunks" // tên bảng mới
                images_table: "hsf_bge_images // tên bảng mới

        + db_path: "EXPERIMENTS/chunk_versions/hsf_bge/vectorchunks_storage"
          collection: "hsf_bge_170526"

        + vectordb_connect_info:
                db_path: "EXPERIMENTS/chunk_versions/hsf_bge/vectorchunks_storage" (sửa tên thành tên thư mục thực nghiệm, vd hsf_bge => hsf_qwen)
                collection: "hsf_bge_170526"  // tên gì cũng đc

        + embedding_provider: "bge" => sửa provider thành provider mới vd bge=> qwen, comment provider cũ lại        
4. Tạo các tables postgres cho thực nghiệm mới:
Mở terminal: 

    B1:
        docker exec -it paradedb bash
    

    B2:
        psql -U postgres -d rag_db

    B3: Chạy các script dưới đây nhưng đổi tên bảng thành tên thực nghiệm (khớp với tên bảng chunks_table và bảng images_table ở bước 3)

            CREATE TABLE hsf_bge_images (
            id BIGSERIAL PRIMARY KEY,
            img_id TEXT UNIQUE,
            base64 TEXT NOT NULL,
            description TEXT
            );

            CREATE TABLE hsf_bge_chunks(
            id BIGSERIAL PRIMARY KEY,
            document_id TEXT UNIQUE,
            search_content TEXT,
            text_content TEXT,
            metadata JSONB
            );

            create index bm25_on_<ten_bang_chunk_moi> on ten_bang_chunk_moi using bm25(id, search_content) with (key_field='id');    

5. Chạy chunk:
    (Kích hoạt môi trường ảo nếu chưa:    .\newvenv\Scripts\activate   )

    python -m src.PIPELINE._3_chunk.strategies.HSF.HSF_chunking  


# GENERATE
Chạy thực nghiệm sinh câu trả lời cho benchmark:

    - Chuyển từ llm gpt-4.1-mini sang llm local cần một model nhận input được cả text+image (vision model)

    - Sau khi cô pull model mong muốn trong ollama và chuẩn bị code cho llm local thì đổi provider về local trong file config của thực nghiệm ạ, tại vì các model hay constraint đều là đọc từ config ra, vd hiện tại nó đang là:
        llm_provider: "openai"
        llm_model: "gpt-4.1-mini"

    - Trong:    ./EXPERIMENTS/full_pipeline_strategies,  
        - tạo thư mục mới (có thể copy từ một thư mục khác như hsf..phía trên)
        - xóa hết các file csv (kết quả thực nghiệm cũ)
        - file run_exp là file chạy thực nghiệm, trong đây có 2 dòng có thể sửa:
            exp_dir = "./EXPERIMENTS/full_pipeline_strategies/hsf_multi_600_2000_nocite/"  <- đường dẫn file câu trả lời của RAG
            input_questions= "./experiment_data/dataset_v2.json" <- đường dẫn file benchmark


    - Chạy exp: python -m src.EXPERIMENTS.full_pipeline_strategies.<ten thu muc thuc nghiem>.run_exp  

    - LLM dùng trong ragas không cần thiết phải đọc được hình ảnh vì các chỉ số đánh giá hoàn toàn dựa vào input của các file csv chỉ có text.      


# XEM DỮ LIỆU trong csdl postgres
    docker exec -it paradedb bash
    psql -U postgres -d rag_db


    xem tất cả các bảng hiện có: 
            \dt;
    
    xem dữ liệu của bảng: select... (lệnh sql thông thường)

    Ngoài ra có thể dùng pgadmin4 với thông tin kết nối là:
            ports:
            - "5435:5432"
            environment:
                POSTGRES_USER: postgres
                POSTGRES_PASSWORD: 123
                POSTGRES_DB: rag_db



                              
