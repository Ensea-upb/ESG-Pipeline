from __future__ import annotations

from pathlib import Path

import yaml

from .models import Company


class CompanyUniverse:
    def __init__(self, config_path: str | Path) -> None:
        self.config_path = Path(config_path)

    def load(self) -> list[Company]:
        payload = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        return [Company.from_dict(item) for item in payload.get("companies", [])]

    def select(self, names_or_all) -> list[Company]:
        companies = self.load()
        if names_or_all == "all":
            return companies

        requested = {str(name).lower() for name in names_or_all}
        return [company for company in companies if company.name.lower() in requested]
