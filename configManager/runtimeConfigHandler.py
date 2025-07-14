from dataclasses import dataclass, field
from typing import Any
from configManager.argumentHandler import parse_arguments

@dataclass
class Config:
    arg: dict[str, Any] = field(default_factory=dict)

    def populate(self) -> None:
        """
        Populate the configuration with parsed arguments.

        Args:
            None

        Returns:
            None
        """
        self.arg.update(parse_arguments())
