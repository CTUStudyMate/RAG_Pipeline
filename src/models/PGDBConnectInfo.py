from dataclasses import dataclass
from typing import Optional

@dataclass
class PGDBConnectInfo:
    host: str
    port: int
    db_name: str
    user: str
    password: str
    table_name: str
    img_table: Optional[str] = None