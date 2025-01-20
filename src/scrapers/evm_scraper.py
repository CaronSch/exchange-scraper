from web3 import Web3
from .base_scraper import BaseScraper
from typing import List, Dict, Any

class EVMScraper(BaseScraper):
    def __init__(self, addresses: List[str], chain_name: str, config: dict):
        super().__init__(addresses, "evm")
        self.w3 = None
        self.chain_name = chain_name
        self.config = config['evm'][chain_name]

    def connect(self) -> None:
        """Connect to EVM node with appropriate authentication"""
        base_url = self.config['url']
        api_key = self.config['api_key']
        
        # Construct URL based on authentication type
        if self.config['api_type'] == 'param':
            provider_url = f"{base_url}?apiKey={api_key}"
            headers = {'content-type': 'application/json', 'Accept-Charset': 'UTF-8'}
        elif self.config['api_type'] == 'bearer':
            provider_url = base_url
            headers = {'content-type': 'application/json', 'Accept-Charset': 'UTF-8', 'Authorization': f"Bearer {api_key}"}
        else:
            raise NotImplementedError(f"Unsupported API type: {self.config['api_type']}")
        
        provider = Web3.HTTPProvider(provider_url, request_kwargs={'headers': headers})
        self.w3 = Web3(provider)
        
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to {self.chain_name} node")

    def get_potential_deposit_addresses(self, block_or_slot: int):
        """Get the transactions in a block that involve watched token accounts"""
        pass

    def validate_potential_deposit_addresses(self):
        """Validate potential deposit addresses and collect funding transactions"""
        pass

    def parse_blocks(self): 
        """Parse blocks and get potential deposit addresses"""
        pass