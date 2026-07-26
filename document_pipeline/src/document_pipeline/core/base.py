"""Abstract base class for all pipeline processing stages."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


class BaseProcessor(ABC, Generic[TInput, TOutput]):
  """Abstract processor that defines the contract for every pipeline stage.

  Each concrete stage must implement ``process`` and accept a strongly typed
  input model, returning a strongly typed output model.
  """

  @abstractmethod
  def process(self, input_data: TInput) -> TOutput:
    """Transform pipeline input into stage output.

    Args:
      input_data: Strongly typed input for this stage.

    Returns:
      Strongly typed output produced by this stage.

    Raises:
      PipelineStageError: If processing fails.
    """
