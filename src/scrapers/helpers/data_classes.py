from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class TokenInfo:
    exchange: str
    wallet: str
    ticker: str
    token_address: str

@dataclass
class FundingData:
    wallet: str
    token_account: str
    transaction_hash: str
    change: float
    block_time: int
    block_or_slot: int
    is_funding_transaction: bool

@dataclass
class TransactionData:
    deposit_wallet: str
    deposit_token_account: str
    signature_index: int
    transaction_hash: str
    transaction_index: int
    account_index: int
    change: float
    block_time: int
    block_or_slot: int
    recipient_token_account: str
    token_info: TokenInfo
    funding_data: List[Dict]
    probability_of_deposit_address: float

