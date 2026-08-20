from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import ProviderResponse, SearchRequest


class Provider(ABC):
    name: str

    @abstractmethod
    def search(self, request: SearchRequest) -> ProviderResponse:
        raise NotImplementedError
