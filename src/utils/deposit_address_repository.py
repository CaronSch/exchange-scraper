from datetime import datetime
import json
from pathlib import Path
from typing import List
import logging
from scrapers.helpers.data_classes import TransactionData


class DepositAddressRepository:
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        logging.info(f"Initializing DepositAddressRepository with path: {self.storage_path}")
        self.storage_path.mkdir(exist_ok=True)

    def save_deposit_addresses(self, tx_data_list: List[TransactionData]) -> dict:
        """
        Saves the deposit addresses to a JSON file.
        
        Args:
            tx_data_list: List of TransactionData objects to save
        """
            
        if not tx_data_list:
            logging.warning("No deposit addresses to save - empty list provided")
            return

        filename = f"deposit_addresses_{datetime.now().isoformat()}.json"
        file_path = self.storage_path / filename
        logging.info(f"Saving deposit addresses to: {file_path}")
        logging.info(f"Number of addresses to save: {len(tx_data_list)}")
        
        # Convert TransactionData objects to serializable dictionaries
        serializable_data = []
        for tx_data in tx_data_list:
            tx_dict = {
                'deposit_wallet': tx_data.deposit_token_account,
                'deposit_token_account': tx_data.deposit_token_account,
                'signature_index': tx_data.signature_index,
                'transaction_hash': tx_data.transaction_hash,
                'transaction_index': tx_data.transaction_index,
                'account_index': tx_data.account_index,
                'change': tx_data.change,
                'block_time': tx_data.block_time,
                'block_or_slot': tx_data.block_or_slot,
                'recipient_token_account': tx_data.recipient_token_account,
                'probability_of_deposit_address': tx_data.probability_of_deposit_address,
                'token_info': {
                    'exchange': tx_data.token_info.exchange,
                    'wallet': tx_data.token_info.wallet,
                    'ticker': tx_data.token_info.ticker,
                    'token_address': tx_data.token_info.token_address
                },
                'funding_data': [{
                    'wallet': fd.wallet,
                    'token_account': fd.token_account,
                    'transaction_hash': fd.transaction_hash,
                    'change': fd.change,
                    'block_time': fd.block_time,
                    'block_or_slot': fd.block_or_slot,
                    'is_funding_transaction': fd.is_funding_transaction
                } for fd in tx_data.funding_data]
            }
            serializable_data.append(tx_dict)

        try:
            with open(file_path, 'w') as f:
                json.dump(serializable_data, f, indent=2)
            logging.info(f"Successfully saved {len(serializable_data)} deposit addresses to {file_path}")
            return serializable_data
        except Exception as e:
            logging.error(f"Error saving deposit addresses: {e}")
            raise

    def get_latest_deposit_file(self) -> Path:
        """
        Gets the most recent deposit addresses file based on the timestamp in the filename.
        
        Returns:
            Path to the most recent file
        """
        files = list(self.storage_path.glob("deposit_addresses_*.json"))
        if not files:
            raise FileNotFoundError(f"No deposit address files found in {self.storage_path}")
            
        # Extract datetime from filename and use it to find the most recent file
        latest_file = max(
            files,
            key=lambda f: datetime.fromisoformat(f.stem.replace('deposit_addresses_', ''))
        )
        
        return latest_file