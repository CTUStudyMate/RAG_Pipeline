from dataclasses import dataclass

@dataclass
class PGDBConnectInfo:
    host: str
    port: int
    db_name: str
    user: str
    password: str
    table_name: str