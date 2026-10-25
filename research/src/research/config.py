# Configuration for experimental evaluation

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ConfigType(str, Enum):
    BASELINE = "A"
    ELEMENT_DECOMP = "B"
    POLARITY_AWARE = "C"
    COMBINED = "D"


@dataclass
class BaselineConfig:
    use_element_decomposition: bool = False
    use_denial_polarity: bool = False
    retrieval_threshold: float = 0.30
    covered_threshold: float = 0.55
    element_covered_ratio: float = 0.60


@dataclass
class ExperimentConfig:
    name: str
    config_type: ConfigType
    baseline: BaselineConfig
    description: str = ""
    
    @classmethod
    def baseline(cls) -> "ExperimentConfig":
        return cls(
            name="baseline",
            config_type=ConfigType.BASELINE,
            baseline=BaselineConfig(use_element_decomposition=False, use_denial_polarity=False),
            description="A - Existing baseline"
        )
    
    @classmethod
    def element_decomp(cls) -> "ExperimentConfig":
        return cls(
            name="element_decomp",
            config_type=ConfigType.ELEMENT_DECOMP,
            baseline=BaselineConfig(use_element_decomposition=True, use_denial_polarity=False),
            description="B - Element decomposition on"
        )
    
    @classmethod
    def polarity_aware(cls) -> "ExperimentConfig":
        return cls(
            name="polarity_aware",
            config_type=ConfigType.POLARITY_AWARE,
            baseline=BaselineConfig(use_element_decomposition=False, use_denial_polarity=True),
            description="C - Denial-polarity filtering on"
        )
    
    @classmethod
    def combined(cls) -> "ExperimentConfig":
        return cls(
            name="combined",
            config_type=ConfigType.COMBINED,
            baseline=BaselineConfig(use_element_decomposition=True, use_denial_polarity=True),
            description="D - Both features on"
        )
    
    @classmethod
    def all_configs(cls) -> list["ExperimentConfig"]:
        return [cls.baseline(), cls.element_decomp(), cls.polarity_aware(), cls.combined()]
