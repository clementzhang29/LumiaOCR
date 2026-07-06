from .base import BaseEngine, OCRResult
from .mineru_engine import MinerUEngine
from .marker_engine import MarkerEngine
from .surya_engine import SuryaEngine
from .docling_engine import DoclingEngine
from .paddle_engine import PaddleOCREngine
from .nougat_engine import NougatEngine
from .dolphin_engine import DolphinEngine

__all__ = [
    "BaseEngine",
    "OCRResult",
    "MinerUEngine",
    "MarkerEngine",
    "SuryaEngine",
    "DoclingEngine",
    "PaddleOCREngine",
    "NougatEngine",
    "DolphinEngine",
]
