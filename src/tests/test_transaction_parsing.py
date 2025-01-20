import json
from pathlib import Path
import pytest
from scrapers.evm_scraper import EVMScraper
from src.scrapers.solana_scraper import SolanaScraper
from solders.transaction import Transaction, VersionedTransaction
from solders.message import Message

# Load test resources
RESOURCE_DIR = Path(__file__).parent / 'resources'

def load_test_transaction(filename: str) -> dict:
    """Load a test transaction from resources"""
    with open(RESOURCE_DIR / filename, 'r') as f:
        raw_tx = json.load(f)
        
        # For legacy transactions
        if raw_tx.get('version') == 'legacy':
            message = Message.from_json(json.dumps(raw_tx['transaction']['message']))
            signatures = raw_tx['transaction']['signatures']
            tx = Transaction(message, signatures)
            tx.meta = raw_tx['meta']
            tx.block_time = raw_tx['blockTime']
            tx.slot = raw_tx['slot']
            return tx
        else:
            # Handle versioned transactions if needed
            return VersionedTransaction.from_json(json.dumps(raw_tx))

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

class TestSolanaTokenCompute:
    @pytest.fixture
    def solana_scraper(self):
        # Mock config for testing
        mock_config = {
            'solana': {
                'url': 'mock_url',
                'api_key': 'mock_key',
                'api_type': 'bearer',
                'rps_limit': 1,
                'tokens': [{
                    'ticker': 'TRUMP',
                    'address': '7rPLJ4VZUdz2pqB9Q5A1mQtpWzbdYBBPc8obSQ8j13jJ'
                }]
            }
        }
        return SolanaScraper({'binance': ['5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9']}, mock_config)

    def test_illegitimate_sol_tx(self, solana_scraper):
        """Tests parsing a Solana transaction"""
        tx = load_test_transaction('sol_binance_illegitimate.json')
        tx = solana_scraper.client.get_transaction(tx.signatures[0], max_supported_transaction_version=10).value
        credit, debit = solana_scraper.compute_token_transfer(2, tx.meta, 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', '5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9', ['58BN4VarBPM3JfBEGPQ1VpAzzzbGgbiv5PvG8VpnmXhh'])

        assert credit == 10000000000000000
