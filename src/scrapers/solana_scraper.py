from solana.rpc.api import Client
import logging
from scrapers.helpers.deposit_metrics import DepositMetrics
from scrapers.helpers.data_classes import FundingData, TokenInfo, TransactionData
from utils.solana_utils import get_associated_token_account
from .base_scraper import BaseScraper
from typing import List, Dict, Any
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import Transaction
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
    def __init__(self, addresses: Dict[str, str], config: dict):
        super().__init__(addresses, "solana")
        self.client = None
        self.config = SolanaConfig.from_dict(config['solana'])
        self.token_accounts = {}
        self.potential_deposit_addresses = []
        self.metrics = DepositMetrics()

        for token in self.config.tokens:
            for exchange, address_list in self.addresses.items():
                for address in address_list:
                    token_account = get_associated_token_account(address, token['address'])
                    self.token_accounts[token_account] = TokenInfo(
                        exchange,
                        address,
                        token['ticker'],
                        token['address']
                    )

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
        
    def parse_blocks(self, start_block_or_slot: int, blocks_to_parse: int = 10):
        """Parse a range of blocks and compute metrics from deposit addresses"""
        for block in range(start_block_or_slot, start_block_or_slot + blocks_to_parse):
            logging.info(f"Parsing block {block}")
            potential_deposit_addresses = self.get_potential_deposit_addresses(start_block_or_slot)
            self.validate_potential_deposit_addresses(potential_deposit_addresses)
        
    def get_potential_deposit_addresses(self, block_or_slot: int) -> List[TransactionData]:
        """Get the transactions in a block that involve watched token accounts"""
        block = self.client.get_block(block_or_slot, max_supported_transaction_version=10)

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

                    signer_token_accounts = [get_associated_token_account(signer, token_info.token_address) for signer in signers]

                    # Search through pre and post token balances
                    (credit, debit) = self.compute_token_transfer(acc_idx, tx.meta, token_info.token_address, token_info.wallet, signers)

                    if not math.isclose(credit, debit, rel_tol=1e-9):
                        logging.info(f"Skipping tx {signature_hash} at slot {block_or_slot} due to credit and debit mismatch: {credit} != {debit}. Not a standard transaction.")
                        pass
                    else:
                        for signature_idx, token_account in enumerate(signer_token_accounts):
                            tx_data = TransactionData(
                                    signers[signature_idx],
                                    token_account,
                                    signature_idx,
                                    signature_hash,
                                    tx_idx,
                                    acc_idx,
                                    credit,
                                    block.value.block_time,
                                    block_or_slot,
                                    str(key),
                                    token_info,
                                    [],
                                    0.0
                                )
                            
                            already_parsed_accounts = [existing_token_account.deposit_token_account for existing_token_account in self.potential_deposit_addresses]
                            
                            if token_account not in already_parsed_accounts:
                                logging.info(f"Found potential deposit address {token_account} at slot {block_or_slot}")
                                self.potential_deposit_addresses.append(tx_data)
                                transactions.append(tx_data)
                            else:
                                logging.info(f"Found existing deposit address {token_account} at slot {block_or_slot}")
                                self.handle_existing_deposit_address(tx, block_or_slot, block.value.block_time, already_parsed_accounts.index(token_account), tx_data)

                        break  # Found a match, no need to check other keys
        return transactions

    def handle_existing_deposit_address(self, tx: Transaction, block_or_slot: int, block_time: int, idx: int, tx_data: TransactionData):
        """Handle existing deposit addresses by finding additional funding transactions"""
        sig = tx.transaction.signatures[0].__str__()
        tx_funding_data = self._process_transactions(sig, tx, block_or_slot, block_time, tx_data, False)
                
        if tx_funding_data is not None:
            self.potential_deposit_addresses[idx].funding_data.append(tx_funding_data)
            sum_of_previous_transfers += tx_funding_data.change
        
    def validate_potential_deposit_addresses(self, potential_deposit_addresses: List[TransactionData]):
        """Validate potential deposit addresses and collect funding transactions"""
        for tx_data in potential_deposit_addresses:
            self._validate_potential_deposit_address(tx_data)

    def _validate_potential_deposit_address(self, tx_data: TransactionData):
        # try:
        previous_signatures = self.client.get_signatures_for_address(
            Pubkey.from_string(tx_data.deposit_token_account),
            before=Signature.from_string(tx_data.transaction_hash)
        )

        sum_of_previous_transfers = 0
        funding_data = []
        i = 0

        for transaction in previous_signatures.value:
            sig = transaction.signature.__str__()
            logging.info(f"Getting transaction {sig} at slot {transaction.slot}")
            tx = self.client.get_transaction(transaction.signature, max_supported_transaction_version=10).value
            tx_funding_data = self._process_transactions(sig, tx.transaction, transaction.slot, transaction.block_time, tx_data, True)
            
            if tx_funding_data is not None:
                funding_data.append(tx_funding_data)
                sum_of_previous_transfers += tx_funding_data.change
            
            i += 1
            if sum_of_previous_transfers >= tx_data.change or i >= 100:
                break
                
        tx_data.funding_data.extend(funding_data)
        tx_data.probability_of_deposit_address = sum_of_previous_transfers / tx_data.change
        logging.info(f"Found deposit token account {tx_data.deposit_token_account} with probability {tx_data.probability_of_deposit_address}")

        # Get older transactions to find additional transfers by the same user"""
        for transaction in previous_signatures.value[i:]:
            tx_funding_data = self._process_transactions(sig, transaction.transaction, transaction.slot, transaction.block_time, tx_data, is_funding_transaction=False)
            
            if tx_funding_data is not None:
                funding_data.append(tx_funding_data)
                sum_of_previous_transfers += tx_funding_data.change
    
        # except Exception as e:
        #     logging.error(f"Error validating potential deposit address in tx {transaction.signature.__str__()}: {str(e)}")
        #     raise(e)

    def _process_transactions(self, sig: str, tx: Transaction, block_or_slot: int, block_time: int, tx_data: TransactionData, is_funding_transaction: bool) -> FundingData:
        """Processes previous signatures to find funding transactions"""
        account_index = tx_data.signature_index
        signers = [tx.transaction.message.account_keys[0].__str__()]
        if len(tx.transaction.signatures) == 2:
            signers.append(tx.transaction.message.account_keys[1].__str__())

        (credit, debit) = self.compute_token_transfer(
            account_index, 
            tx.meta, 
            tx_data.token_info.token_address, 
            tx_data.deposit_wallet,
            signers
        )

        if not math.isclose(credit, debit, rel_tol=1e-9):
            logging.info(f"Skipping tx {sig} at slot {block_or_slot} due to credit and debit mismatch: {credit} != {debit}. Not a standard transaction.")
            return None
        else:
            signer_token_accounts = [get_associated_token_account(signer, tx_data.token_info.token_address) for signer in signers]

            return FundingData(
                signers,
                signer_token_accounts,
                sig,
                credit,
                block_time,
                block_or_slot,
                is_funding_transaction
            )

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
            """Double-check that these are actually the token balances we are targeting"""
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