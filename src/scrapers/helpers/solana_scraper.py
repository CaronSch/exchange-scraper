from solana.rpc.api import Client
import logging
from scrapers.helpers.deposit_metrics import DepositMetrics
from src.scrapers.helpers.data_classes import FundingData, TransactionData
from utils.solana_utils import get_associated_token_account
from .base_scraper import BaseScraper
from typing import List, Dict, Any
from solders.pubkey import Pubkey
from solders.signature import Signature
import math
from utils.rate_limiter import RateLimiter
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SolanaConfig:
    url: str
    api_key: str
    api_type: str
    rps_limit: int
    tokens: List[Dict[str, str]]

    @classmethod
    def from_dict(cls, config: Dict) -> 'SolanaConfig':
        return cls(**config)

class RateLimitedSolanaClient(Client):
    def __init__(self, *args, rps_limit: int = 1, **kwargs):
        super().__init__(*args, **kwargs)
        self.rate_limiter = RateLimiter(rps_limit)
        
        # Apply rate limiter to all public methods
        for attr_name in dir(self):
            if not attr_name.startswith('_'):  # Only public methods
                attr = getattr(self, attr_name)
                if callable(attr):
                    setattr(self, attr_name, self.rate_limiter(attr))

class SolanaScraper(BaseScraper):
    def __init__(self, addresses: List[str], config: dict):
        super().__init__(addresses, "solana")
        self.client = None
        self.config = SolanaConfig.from_dict(config['solana'])
        self.token_accounts = {}
        self.potential_deposit_addresses = []
        self.metrics = DepositMetrics()

        for token in self.config.tokens:
            for exchange, address_list in self.addresses.items():
                for address in address_list:
                    token_account = get_associated_token_account(address, token['mint'])
                    self.token_accounts[token_account] = {
                        "exchange": exchange,
                        "wallet": address,
                        "ticker": token['ticker'],
                        "mint": token['mint']
                    }

    def connect(self) -> None:
        """Connect to Solana node with appropriate authentication"""
        base_url = self.config.url
        api_key = self.config.api_key
        
        # Construct client with appropriate authentication
        if self.config.api_type == 'param':
            url = f"{base_url}?apiKey={api_key}"
            self.client = RateLimitedSolanaClient(base_url, rps_limit=self.config.rps_limit)
        else:  # bearer type
            headers = {'Authorization': f"Bearer {api_key}"}
            self.client = RateLimitedSolanaClient(base_url, extra_headers=headers, rps_limit=self.config.rps_limit)
            
        try:
            self.client.get_version()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Solana node: {e}")
        
    def get_latest_transactions(self) -> List[Dict[str, Any]]:
        """Get latest transactions involving watched addresses"""
        transactions = []
        rps_limit = self.config.rps_limit
        
        for exchange in self.token_accounts.keys():
            for token_account in self.token_accounts[exchange]:
                pubkey = Pubkey.from_string(token_account)
                # Get recent transactions for each address
                response = self.client.get_signatures_for_address(pubkey)
                if response.value:
                    for tx_info in response.value:
                        tx = self.client.get_transaction(tx_info.signature, max_supported_transaction_version=10)
                        if tx.value:
                            transactions.append(self.parse_transaction(tx.value))
        
        return transactions
    
    def parse_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Solana transaction into standard format"""
        meta = transaction.transaction.meta
        tx = transaction.transaction.transaction
        account_keys = tx.message.account_keys
        return {
            'hash': tx.signatures,
            'from': account_keys[0].__str__,
            'to': account_keys[1].__str__,
            'value': meta.post_balances[0] - meta.pre_balances[0],
            'timestamp': transaction.block_time,
            'chain': 'solana'
        } 
    
    def get_potential_deposit_addresses(self, slot: int):
        """Get the transactions in a block that involve watched token accounts"""
        block = self.client.get_block(slot, max_supported_transaction_version=10)

        transactions = []
        for tx_idx, tx in enumerate(block.value.transactions):
            # Check if any account key matches our watched token accounts
            for acc_idx, key in enumerate(tx.transaction.message.account_keys):
                if str(key) in self.token_accounts.keys():
                    # Find matching token balance entry
                    pre_balance = None
                    post_balance = None
                    token_info = self.token_accounts[str(key)]
                    signature_hash = tx.transaction.signatures[0].__str__()

                    signers = [tx.transaction.message.account_keys[0].__str__()]
                    if len(tx.transaction.signatures) == 2:
                        signers.append(tx.transaction.message.account_keys[1].__str__())

                    signer_token_accounts = [get_associated_token_account(signer, token_info['mint']) for signer in signers]

                    # Search through pre and post token balances
                    (credit, debit) = self.compute_token_transfer(acc_idx, tx.meta, token_info['mint'], token_info['wallet'], signers)

                    if not math.isclose(credit, debit, rel_tol=1e-9):
                        logging.info(f"Skipping tx {signature_hash} at slot {slot} due to credit and debit mismatch: {credit} != {debit}. Not a standard transaction.")
                        pass
                    else:
                        tx_data = TransactionData(
                            signers,
                            signer_token_accounts,
                            signature_hash,
                            tx_idx,
                            acc_idx,
                            credit,
                            block.value.block_time,
                            slot,
                            str(key),
                            token_info,
                            [],
                            0.0
                        )

                        logging.info(f"Found potential deposit address {signers} at slot {slot}")

                        self.potential_deposit_addresses.append(tx_data)
                        break  # Found a match, no need to check other keys
                    
    def validate_potential_deposit_addresses(self):
        """Validate potential deposit addresses"""

        for tx_data in self.potential_deposit_addresses:
            for idx, potential_token_account in enumerate(tx_data.potential_token_accounts):
                previous_signatures = self.client.get_signatures_for_address(
                    Pubkey.from_string(potential_token_account),
                    before=Signature.from_string(tx_data.transaction)
                )

                sum_of_previous_transfers = 0
                funding_data = []
                i = 0

                for signature in previous_signatures.value:
                    logging.info(f"Getting transaction {signature.signature.__str__()} at slot {signature.slot}")

                    tx = self.client.get_transaction(signature.signature, max_supported_transaction_version=10).value
                    signers = [tx.transaction.transaction.message.account_keys[0].__str__()]
                    if len(tx.transaction.transaction.signatures) == 2:
                            signers.append(tx.transaction.transaction.message.account_keys[1].__str__())

                    (credit, debit) = self.compute_token_transfer(
                        idx, 
                        tx.transaction.meta, 
                        tx_data.token_info.token_address, 
                        tx_data.potential_deposit_wallets[idx],
                        signers
                    )

                    if not math.isclose(credit, debit, rel_tol=1e-9):
                        logging.info(f"Skipping tx {signature.signature.__str__()} at slot {tx.slot} due to credit and debit mismatch: {credit} != {debit}. Not a standard transaction.")
                        pass
                    else:
                        signer_token_accounts = [get_associated_token_account(signer, tx_data.token_info.token_address) for signer in signers]

                        tx_funding_data = FundingData(
                            signers,
                            signer_token_accounts,
                            signature.signature.__str__(),
                            credit,
                            tx.block_time,
                            tx.slot
                        )
                        funding_data.append(tx_funding_data)
                        sum_of_previous_transfers += credit
                    
                    i += 1
                    if sum_of_previous_transfers >= tx_data.change or i >= 100:
                        break

                        
                tx_data.funding_data.extend(funding_data)
                tx_data.probability_of_deposit_address = sum_of_previous_transfers / tx_data.change
                logging.info(f"Found deposit wallet {tx_data.potential_deposit_wallets[idx]} with probability {tx_data.probability_of_deposit_address}")

                        
    def parse_blocks(self):
        # slot = self.client.get_slot().value
        slot = 315053829

        self.get_potential_deposit_addresses(slot)
        self.validate_potential_deposit_addresses()
        self.metrics.compute_metrics()

    def compute_token_transfer(self, account_index: int, meta: Dict[str, Any], mint: str, receiving_owner: str, funding_owners: List[str]) -> tuple[float, float]:
        """
        Compute token transfer amounts and validate ownership/mint
        Returns: (credit, debit) tuple
        """
        balances = {
            'pre_receiver': 0,
            'pre_sender': 0,
            'post_receiver': 0,
            'post_sender': 0
        }

        def validate_and_get_balance(balance, balance_type: str):
            assert balance.mint.__str__() == mint, f"Mint mismatch: {balance.mint} != {mint}"
            if balance_type == 'receiver':
                assert balance.owner.__str__() == receiving_owner, f"Owner mismatch: {balance.owner} != {receiving_owner}"
            return balance.ui_token_amount.ui_amount or 0

        for balance in meta.pre_token_balances:
            if balance.account_index == account_index:
                balances['pre_receiver'] = validate_and_get_balance(balance, 'receiver')
            if balance.owner.__str__() in funding_owners:
                balances['pre_sender'] = validate_and_get_balance(balance, 'sender')

        for balance in meta.post_token_balances:
            if balance.account_index == account_index:
                balances['post_receiver'] = validate_and_get_balance(balance, 'receiver')
            if balance.owner.__str__() in funding_owners:
                balances['post_sender'] = validate_and_get_balance(balance, 'sender')

        credit = balances['post_receiver'] - balances['pre_receiver']
        debit = balances['pre_sender'] - balances['post_sender']

        return credit, debit