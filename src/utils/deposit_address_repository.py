from datetime import datetime
import json
from pathlib import Path
from scrapers.helpers.data_classes import TransactionData


class DepositAddressRepository:
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)

    def save_deposit_address(self, deposit_data: TransactionData):
        filename = f"deposit_{deposit_data.transaction}_{datetime.now().isoformat()}.json"
        with open(self.storage_path / filename, 'w') as f:
            json.dump(deposit_data.__dict__, f, indent=2)