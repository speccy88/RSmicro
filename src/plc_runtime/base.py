from __future__ import annotations

from abc import ABC, abstractmethod
from importlib import resources
from typing import Any

from plc_ascii.model import Program


class BoardRuntime(ABC):
    """Shared base class for board-specific runtime installers/builders."""

    target_name = "runtime"

    @property
    def package_name(self) -> str:
        return self.__class__.__module__.rsplit(".", 1)[0]

    def resource_text(self, name: str) -> str:
        return resources.files(self.package_name).joinpath(name).read_text(encoding="utf-8")

    @abstractmethod
    def board_files(self, program: Program | None = None, **kwargs: Any) -> dict[str, str]:
        """Return the exact files that are loaded onto the target board."""

