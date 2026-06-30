"""Export collected business records into multiple file formats."""

from __future__ import annotations

import json
import logging
from dataclasses import fields
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import AppConfig
from app.models import Business


class Exporter:
    """Handle writing extracted business records to disk."""

    def __init__(
        self,
        config: AppConfig,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the exporter with configuration and logging support."""

        self.config = config
        self.logger = logger or logging.getLogger(__name__)

    def create_output_directory(self) -> Path:
        """Ensure the output directory exists and return its path."""

        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        return self.config.output_dir

    def export_excel(self, businesses: list[Business]) -> Path:
        """Export business records to an Excel file and return the file path."""

        output_path = self.create_output_directory() / self.config.excel_file_name
        self._to_dataframe(businesses).to_excel(output_path, index=False)
        self.logger.info("Excel export created at %s", output_path)
        return output_path

    def export_csv(self, businesses: list[Business]) -> Path:
        """Export business records to a CSV file and return the file path."""

        output_path = self.create_output_directory() / self.config.csv_file_name
        self._to_dataframe(businesses).to_csv(output_path, index=False)
        self.logger.info("CSV export created at %s", output_path)
        return output_path

    def export_json(self, businesses: list[Business]) -> Path:
        """Export business records to a JSON file and return the file path."""

        output_path = self.create_output_directory() / self.config.json_file_name
        records = [business.to_dict() for business in businesses]
        with output_path.open("w", encoding="utf-8") as file_pointer:
            json.dump(records, file_pointer, indent=4, ensure_ascii=False)
        self.logger.info("JSON export created at %s", output_path)
        return output_path

    def _to_dataframe(self, businesses: list[Business]) -> pd.DataFrame:
        """Convert business objects into a predictable DataFrame schema."""

        expected_columns = [field.name for field in fields(Business)]
        records: list[dict[str, Any]] = [business.to_dict() for business in businesses]

        if not records:
            return pd.DataFrame(columns=expected_columns)

        dataframe = pd.DataFrame(records)
        return dataframe.reindex(columns=expected_columns)
