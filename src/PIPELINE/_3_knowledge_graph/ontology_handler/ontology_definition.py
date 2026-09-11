from typing import Literal
# a coarse-grained, domain-agnostic entity schema
ENTITY_TYPES = Literal[
    "CONCEPT",
    "OBJECT",
    "METHOD",
    "PROCESS",
    "SYSTEM",
    "PROPERTY",
    "ARTIFACT",
    "PERSON",
    "ORGANIZATION",
    "LOCATION",
    "EVENT",
    "OTHER",
]

## expected shape should include:
#     {
#   "canonical_name": "Superclass",
#   "aliases": [
#     "Parent class",
#     "Base class"
#   ]
# }

# | Type           | Dùng cho                                               | Ví dụ                                             |
# | -------------- | ------------------------------------------------------ | ------------------------------------------------- |
# | `CONCEPT`      | Khái niệm, lý thuyết, nguyên lý, định luật             | NoSQL, polymorphism, natural selection            |
# | `OBJECT`       | Đối tượng vật lý hoặc đối tượng cụ thể được nghiên cứu | neuron, molecule, transistor, organism            |
# | `METHOD`       | Phương pháp, thuật toán, kỹ thuật                      | binary search, PCR, gradient descent              |
# | `PROCESS`      | Quá trình, cơ chế, chuỗi hoạt động                     | cell division, query execution, photosynthesis    |
# | `SYSTEM`       | Hệ thống gồm nhiều thành phần tương tác                | DBMS, operating system, nervous system            |
# | `PROPERTY`     | Thuộc tính, đại lượng, đặc điểm có thể quan sát/đo     | consistency, mass, latency, reliability           |
# | `ARTIFACT`     | Sản phẩm hoặc cấu trúc do con người tạo ra             | programming language, protocol, dataset, equation |
# | `PERSON`       | Cá nhân                                                | Alan Turing                                       |
# | `ORGANIZATION` | Công ty, trường, tổ chức                               | Microsoft, W3C                                    |
# | `LOCATION`     | Địa điểm, khu vực                                      | Europe, Pacific Ocean                             |
# | `EVENT`        | Sự kiện cụ thể                                         | Industrial Revolution                             |
# | `OTHER`        | Entity quan trọng chưa thuộc loại nào                  | fallback                                          |

RELATION_TYPES =Literal[
    # Identity and classification
    "IS_A",
    "INSTANCE_OF",
    "DEFINED_AS",
    "SYNONYM_OF",
    "DISTINCT_FROM",
    "EXEMPLIFIES",

    # Structure and composition
    "PART_OF",
    "HAS_PART",
    "MADE_OF",
    "HAS_PROPERTY",

    # Function and dependency
    "USED_FOR",
    "CAPABLE_OF",
    "USES",
    "REQUIRES",
    "DEPENDS_ON",
    "ENABLES",
    "IMPLEMENTS",
    "ASSESSES_NEED_FOR",
    "APPLICABLE_TO"

    # Causality and results
    "CAUSES",
    "AFFECTS",
    "PRODUCES",
    "CREATED_BY",
    "DERIVED_FROM",

    # Processes and time
    "HAS_SUBPROCESS",
    "PRECEDES",

    # Space and representation
    "LOCATED_IN",
    "REPRESENTS",
    "MEASURES",

    # Comparison and argumentation
    "SIMILAR_TO",
    "CONTRASTS_WITH",
    "SUPPORTS",
    "CONTRADICTS",

    # Fallback
    "RELATED_TO",
]

## expected relationship shape:
# {
#   "source": "Horizontal scalability",
#   "target": "Consistency",
#   "relation_type": "AFFECTS",
#   "description": "Achieving horizontal scalability across distributed nodes can require trade-offs in consistency.",
#   "evidence_chunk_ids": ["chunk_171", "chunk_203"]
# }

RELATION_TYPE_CONSTRAINTS = {
    "PRECEDES": {
        "source_types": {"PROCESS", "EVENT"},
        "target_types": {"PROCESS", "EVENT"},
    },
    "HAS_SUBPROCESS": {
        "source_types": {"PROCESS"},
        "target_types": {"PROCESS"},
    },
    "PRODUCES": {
        "source_types": {
            "PERSON",
            "ORGANIZATION",
            "SYSTEM",
            "METHOD",
            "PROCESS",
        },
        "target_types": {
            "ARTIFACT",
            "SYSTEM",
            "CONCEPT",
            "OTHER",
        },
    },
    "ASSESSES_NEED_FOR": {
        "source_types": {"METHOD", "PROCESS"},
        "target_types": {"SYSTEM", "ARTIFACT", "METHOD", "PROCESS"},
    },
    "INSTANCE_OF": {
        "target_types": {"CONCEPT"},
    },
}