from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OCRResult:
    markdown: str = ""
    json_data: Optional[dict] = None
    metadata: dict = field(default_factory=dict)
    pages: list[dict] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None
    engine: str = ""
    processing_time: float = 0.0


class BaseEngine(ABC):
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.name = self.__class__.__name__

    @abstractmethod
    async def convert(self, pdf_path: str, **kwargs) -> OCRResult:
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        ...

    @abstractmethod
    def get_metadata(self) -> dict:
        ...