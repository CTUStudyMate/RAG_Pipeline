from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel
import yaml
from pathlib import Path


# -------- DB models --------
class PGDBConnectInfo(BaseModel):
    host: str
    port: int
    db_name: str
    user: str
    password: str
    chunks_table: str | None = None
    images_table: str | None = None


class VectorDBConnectInfo(BaseModel):
    db_path: str
    collection: str


# -------- main settings --------
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # raw env (secrets)
    pgdb_host: str
    pgdb_port: int
    pgdb_name: str
    pgdb_user: str
    pgdb_password: str
    
    #pgdb_chunks_table
    #pgdb_imgs_table

    # loaded yaml
    config: dict

    @classmethod
    def load(cls, config_path: str, env_file=".env"):
        data = yaml.safe_load(Path(config_path).read_text())

        return cls(
            config=data,
        )


    @property
    def pgdb_connect_info(self) -> PGDBConnectInfo:
        return PGDBConnectInfo(
            host=self.pgdb_host,
            port=self.pgdb_port,
            db_name=self.pgdb_name,
            user=self.pgdb_user,
            password=self.pgdb_password,
            chunks_table=self.config["pgdb"]["chunks_table"],
            images_table=self.config["pgdb"]["images_table"],
        )
            