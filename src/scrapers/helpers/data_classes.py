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
    token_address: str
    ticker: str
    change: float
    block_time: int
    block: int

@dataclass
class TransactionData:
    potential_deposit_wallets: List[str]
    potential_token_accounts: List[str]
    transaction: str
    transaction_index: int
    key_index: int
    change: float
    block_time: int
    block: int
    recipient_token_account: str
    token_info: TokenInfo
    funding_data: List[Dict]
    probability_of_deposit_address: float

