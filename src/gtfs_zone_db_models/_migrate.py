import importlib.resources

from alembic import command
from alembic.config import Config


def main() -> None:
    alembic_path = importlib.resources.files("gtfs_zone_db_models").joinpath("alembic")
    cfg = Config()
    cfg.set_main_option("script_location", str(alembic_path))
    cfg.set_main_option("version_path_separator", "os")
    command.upgrade(cfg, "head")
