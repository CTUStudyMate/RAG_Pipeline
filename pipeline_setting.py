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
    
    config: dict
    
    @staticmethod
    def deep_merge(base: dict, override: dict):
        result = dict(base)

        for k, v in override.items():
            if (
                k in result
                and isinstance(result[k], dict)
                and isinstance(v, dict)
            ):
                result[k] = Settings.deep_merge(result[k], v)
            else:
                result[k] = v

        return result  

    @classmethod
    def load(cls, config_path: str, env_file=".env"):
        data = yaml.safe_load(Path(config_path).read_text())
        data = dict(data)
        chunk_path_str = data.pop("chunk_config", None)
        chunk_cfg = {}
        if chunk_path_str:
            chunk_cfg = yaml.safe_load(Path(chunk_path_str).read_text())

        merged_config = Settings.deep_merge(chunk_cfg, data)


        return cls(
            config=merged_config,
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
        
      
            