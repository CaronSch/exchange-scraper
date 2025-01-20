from collections import defaultdict
from .data_classes import TransactionData

class DepositMetrics:
    def __init__(self):
        self.metrics = defaultdict(lambda: {
            'total_deposits': 0,
            'total_volume': 0.0,
            'avg_funding_txs': 0.0,
            'deposit_frequencies': defaultdict(int)
        })

    def update_metrics(self, deposit_data: TransactionData):
        token = deposit_data.token_info.ticker
        self.metrics[token]['total_deposits'] += 1
        self.metrics[token]['total_volume'] += deposit_data.change
        
        if deposit_data.funding_data:
            self.metrics[token]['avg_funding_txs'] = (
                (self.metrics[token]['avg_funding_txs'] * (self.metrics[token]['total_deposits'] - 1) +
                len(deposit_data.funding_data)) / self.metrics[token]['total_deposits']
            )