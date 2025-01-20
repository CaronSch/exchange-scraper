import json
from pathlib import Path
import pytest
from src.scrapers.evm_scraper import EVMScraper
from src.scrapers.solana_scraper import SolanaScraper

# Load test resources
RESOURCE_DIR = Path(__file__).parent / 'resources'

def load_test_transaction(filename: str) -> dict:
    """Load a test transaction from resources"""
    with open(RESOURCE_DIR / filename, 'r') as f:
        return json.load(f)

# class TestEVMTransactionParsing:
#     @pytest.fixture
#     def evm_scraper(self):
#         # Mock config for testing
#         mock_config = {
#             'evm': {
#                 'ethereum': {
#                     'url': 'mock_url',
#                     'api_key': 'mock_key',
#                     'api_type': 'bearer',
#                     'rps_limit': 1
#                 }
#             }
#         }
#         return EVMScraper(['0x742d35Cc6634C0532925a3b844Bc454e4438f44e'], 'ethereum', mock_config)

#     def test_parse_eth_transfer(self, evm_scraper):
#         """Test parsing a basic ETH transfer transaction"""
#         raw_tx = load_test_transaction('eth_tx.json')
#         parsed_tx = evm_scraper.parse_transaction(raw_tx, 1678901234)

#         assert parsed_tx['hash'] == raw_tx['hash']
#         assert parsed_tx['from'] == raw_tx['from']
#         assert parsed_tx['to'] == raw_tx['to']
#         assert isinstance(parsed_tx['value'], float)
#         assert parsed_tx['timestamp'] == 1678901234
#         assert parsed_tx['chain'] == 'ethereum'

class TestSolanaTransactionParsing:
    @pytest.fixture
    def solana_scraper(self):
        # Mock config for testing
        mock_config = {
            'solana': {
                'url': 'mock_url',
                'api_key': 'mock_key',
                'api_type': 'bearer',
                'rps_limit': 1
            }
        }
        return SolanaScraper(['5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9'], mock_config)

    def test_legitimate_sol_tx(self, solana_scraper):
        """Tests parsing a Solana transaction"""
        raw_tx = load_test_transaction('sol_binance_legitimate.json')
        parsed_tx = solana_scraper.parse_transaction(raw_tx)

        assert parsed_tx['hash'] == raw_tx['transaction']['signatures'][0]
        assert isinstance(parsed_tx['from'], str)
        assert isinstance(parsed_tx['to'], str)
        assert isinstance(parsed_tx['value'], int)
        assert isinstance(parsed_tx['timestamp'], int)
        assert parsed_tx['chain'] == 'solana' 