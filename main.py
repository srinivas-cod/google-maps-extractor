"""Entry point for the Google Maps Business Extractor."""

from __future__ import annotations

from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - graceful fallback for incomplete local envs.
    def load_dotenv(*args: object, **kwargs: object) -> bool:
        """Fallback dotenv loader when python-dotenv is unavailable."""

        return False

from app.config import AppConfig
from app.exporter import Exporter
from app.logger import get_logger
from app.scraper import Scraper


def _read_keyword(config: AppConfig, logger_name: str) -> str:
    """Read the search keyword from terminal input."""

    logger = get_logger(logger_name, config)
    try:
        keyword = input(config.input_prompt).strip()
    except EOFError:
        logger.warning("No terminal input available. Proceeding with an empty keyword.")
        return ""
    return keyword


def main() -> int:
    """Run the application bootstrap and placeholder extraction workflow."""

    project_root = Path(__file__).resolve().parent
    load_dotenv(project_root / ".env")

    config = AppConfig.from_env()
    logger = get_logger(config=config)

    try:
        keyword = _read_keyword(config, logger.name)
        if not keyword:
            logger.warning("No keyword provided. Exiting without starting extraction.")
            return 0

        scraper = Scraper(keyword=keyword, config=config, logger=logger)
        exporter = Exporter(config=config, logger=logger)

        try:
            records = scraper.run()
        except KeyboardInterrupt:
            logger.warning("Scraping manually interrupted by user! Exporting partial results...")
            records = getattr(scraper, "_processed_businesses", [])
        excel_path = exporter.export_excel(records)
        csv_path = exporter.export_csv(records)
        json_path = exporter.export_json(records)

        logger.info(
            "Extraction summary | keyword='%s' | records=%s | excel=%s | csv=%s | json=%s",
            keyword,
            len(records),
            excel_path,
            csv_path,
            json_path,
        )
        return 0
    except Exception:
        logger.exception("Application terminated due to an unexpected error.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
