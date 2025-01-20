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

    def get_latest_transactions(self) -> List[Dict[str, Any]]:
        """Get latest transactions involving watched addresses"""
        transactions = []
        latest_block = self.w3.eth.block_number
        
        # Respect RPS limit from config
        rps_limit = self.config.get('rps_limit', 1)
        blocks_to_scan = 10  # Consider making this configurable
        
        # Scan last N blocks
        for block_number in range(latest_block - blocks_to_scan, latest_block + 1):
            block = self.w3.eth.get_block(block_number, full_transactions=True)
            block_timestamp = block.timestamp
            for tx in block.transactions:
                if tx['to'] in self.addresses or tx['from'] in self.addresses:
                    tx_data = self.parse_transaction(tx, block_timestamp)
                    transactions.append(tx_data)
        
        return transactions

    def parse_transaction(self, transaction: Dict[str, Any], block_timestamp: int) -> Dict[str, Any]:
        """Parse EVM transaction into standard format"""
        return {
            'hash': transaction['hash'].hex(),
            'from': transaction['from'],
            'to': transaction['to'],
            'value': self.w3.from_wei(transaction['value'], 'ether'),
            'timestamp': block_timestamp,
            'chain': self.chain_name
        } 