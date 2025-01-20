from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import timedelta

class BaseScraper(ABC):
    def __init__(self, addresses: List[str], chain_type: str):
        self.addresses = addresses
        self.chain_type = chain_type

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to blockchain node"""
        pass

    @abstractmethod
    def get_potential_deposit_addresses(self, block_or_slot: int):
        """Get the transactions in a block that involve watched token accounts"""
        pass

    @abstractmethod
    def validate_potential_deposit_addresses(self):
        """Validate potential deposit addresses and collect funding transactions"""
        pass 

    def parse_blocks(self):
        """Parse blocks and get potential deposit addresses"""
        pass