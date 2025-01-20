from abc import ABC, abstractmethod
from typing import List, Dict, Any
from utils.cache import cache_transactions
from datetime import timedelta

class BaseScraper(ABC):
    def __init__(self, addresses: List[str], chain_type: str):
        self.addresses = addresses
        self.chain_type = chain_type

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to blockchain node"""
        pass

    @cache_transactions(cache_duration=timedelta(hours=1))
    @abstractmethod
    def get_latest_transactions(self) -> List[Dict[str, Any]]:
        """Fetch and parse recent transactions for monitored addresses"""
        pass

    @abstractmethod
    def parse_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a single transaction into standardized format"""
        pass 

    # TODO: add error handling