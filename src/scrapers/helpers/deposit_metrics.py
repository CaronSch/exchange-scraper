from collections import defaultdict
from datetime import datetime
import json
import logging
import statistics
from typing import Dict, List
from .data_classes import TransactionData
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

class DepositMetrics:
    def __init__(self):
        self.deposit_data = []
        self.min_slot = None
        self.max_slot = None

    def load_deposit_data(self, file_name: str):
        """Load the latest deposit data from the repository"""
        try:
            with open(file_name, "r") as f:
                self.deposit_data = json.load(f)
        except FileNotFoundError:
            logging.error("No deposit data found")
            self.deposit_data = []

    def compute_metrics(self, deposit_data: List[dict]):
        volumes = self.aggregate_funding_volume(deposit_data)
        logging.info(self.format_funding_volume(volumes))

    def aggregate_funding_volume(self, deposit_data: List[dict]) -> dict:
        """
        Aggregates funding volume by token ticker and exchange.
        
        Args:
            deposit_data: List of deposit data dictionaries
            
        Returns:
            Dictionary with structure {(ticker, exchange): total_volume}
        """
        aggregated_stats = {}
        time_series_stats = {}
        
        for deposit in deposit_data:
            if deposit['probability_of_deposit_address'] < 0.8:
                continue
            ticker = deposit['token_info']['ticker']
            exchange = deposit['token_info']['exchange']
            key = (ticker, exchange)

            self.min_slot = min(self.min_slot or deposit['block_or_slot'], deposit['block_or_slot'])
            self.max_slot = max(self.max_slot or deposit['block_or_slot'], deposit['block_or_slot'])

            if not deposit['funding_data']:
                continue
                
            # Get funding transactions
            funding_txs = [
                tx for tx in deposit['funding_data']
            ]
            
            if not funding_txs:
                continue
            
            # Sum up all funding transaction changes
            funding_volume = sum(
                funding['change'] 
                for funding in funding_txs
            )

            senders = list(
                funding['token_account']
                for funding in funding_txs
            )

            # Get funding transactions that were part of a sweep into the exchange hot wallet
            sweep_txs = [
                tx for tx in deposit['funding_data']
                if tx.get('is_funding_transaction', True)
            ]

            funding_volume_until_sweep = sum(
                funding['change'] 
                for funding in sweep_txs
            )

            sweep_timespan = max(tx['block_time'] for tx in sweep_txs) - min(tx['block_time'] for tx in sweep_txs)
            
            # Add to existing total or create new entry
            if key in aggregated_stats:
                aggregated_stats[key]['wallet_sweeps'] += 1
                aggregated_stats[key]['volume'] += funding_volume
                aggregated_stats[key]['volume_until_sweep'] += funding_volume_until_sweep
                aggregated_stats[key]['time_between_deposits'].append(sweep_timespan / len(sweep_txs))
                aggregated_stats[key]['senders'].extend(senders)
            else:
                aggregated_stats[key] = {
                    'wallet_sweeps': 1,
                    'volume': funding_volume,
                    'volume_until_sweep': funding_volume_until_sweep,
                    'time_between_deposits': [sweep_timespan / len(sweep_txs)],
                    'senders': senders
                }

            sweep_time = deposit['block_time']
            if 'sweep' in time_series_stats:
                time_series_stats['sweep'][sweep_time] += deposit['change']
            else:
                time_series_stats['sweep'] = {}
                time_series_stats['sweep'][sweep_time] = deposit['change']

            for fund_tx in sweep_txs:
                timestamp = fund_tx['block_time']
                if 'fund' in time_series_stats:
                    if timestamp in time_series_stats['fund']:
                        time_series_stats['fund'][timestamp] += fund_tx['change']
                    else:
                        time_series_stats['fund'][timestamp] = fund_tx['change']
                else:
                    time_series_stats['fund'] = {
                        timestamp: fund_tx['change']
                    }

        return aggregated_stats, time_series_stats


    def format_funding_volume(self, aggregated_volume: dict) -> str:
        """
        Formats the aggregated volume data into a readable string.
        
        Args:
            aggregated_volume: Dictionary with structure {(ticker, exchange): total_volume}
            
        Returns:
            Formatted string showing volumes by token and exchange
        """
        output = []
        num_blocks = self.max_slot - self.min_slot + 1
        for (ticker, exchange), stats in sorted(aggregated_volume.items()):
            unique_senders = len(list(set(stats['senders'])))
            sender_count = len(stats['senders'])

            output.append(f"="*20)
            output.append(f"${ticker} on {exchange}:")
            output.append(f"Total sweeps from deposit addresses to exchange hot wallet: {stats['wallet_sweeps']}")
            output.append(f"Total depositors: {sender_count} of which {unique_senders} are unique.")
            output.append(f"Average depositor per exchange sweep: {sender_count/stats['wallet_sweeps']:.2f}")
            output.append(f"Average time between deposits: {statistics.mean(stats['time_between_deposits']):.2f}")
            output.append("-"*20)
            output.append(f"Total volume: {stats['volume']:,.2f} {ticker}")
            output.append(f"Average volume per block: {stats['volume']/num_blocks:,.2f}")
            output.append(f"Average volume per transaction: {stats['volume']/sender_count:,.2f}")
            output.append("-"*20)
            output.append(f"Total volume until sweep: {stats['volume_until_sweep']:,.2f} {ticker}")
            output.append(f"Average volume per block: {stats['volume_until_sweep']/num_blocks:,.2f}")
            output.append(f"Average volume per transaction: {stats['volume_until_sweep']/sender_count:,.2f}")
        return "\n".join(output)
    
    def plot_time_series(self, time_series_stats: Dict[str, Dict[int, float]], save_path: str = None):
        """
        Creates a bar chart of funding and sweep volumes over time, grouped by hour.
        
        Args:
            time_series_stats: Dictionary with structure {
                'fund': {timestamp: volume, ...},
                'sweep': {timestamp: volume, ...}
            }
            save_path: Optional path to save the plot. If None, displays the plot.
        """
        plt.figure(figsize=(15, 8))
        
        # Group data by hour
        def group_by_hour(time_series: Dict[int, float]) -> Dict[datetime, float]:
            hourly_data = defaultdict(float)
            for timestamp, volume in time_series.items():
                # Convert to datetime and truncate to hour
                dt = datetime.fromtimestamp(timestamp)
                hour_dt = dt.replace(minute=0, second=0, microsecond=0)
                hourly_data[hour_dt] += volume
            return dict(sorted(hourly_data.items()))
        
        # Process both series
        fund_hourly = group_by_hour(time_series_stats['fund'])
        sweep_hourly = group_by_hour(time_series_stats['sweep'])
        
        # Get all unique hours for consistent x-axis
        all_hours = sorted(set(fund_hourly.keys()) | set(sweep_hourly.keys()))
        
        # Create the bar chart
        bar_width = 0.35  # Width of bars
        
        # Convert hours to numbers for plotting
        x = range(len(all_hours))
        
        # Plot bars
        plt.bar([i - bar_width/2 for i in x], 
            [fund_hourly.get(hour, 0) for hour in all_hours],
            bar_width, 
            alpha=0.7, 
            label='Funding', 
            color='blue')
            
        plt.bar([i + bar_width/2 for i in x], 
                [sweep_hourly.get(hour, 0) for hour in all_hours],
                bar_width, 
                alpha=0.7, 
                label='Sweep', 
                color='red')
        
        # Customize the plot
        plt.title('Hourly Funding and Sweep Volumes')
        plt.xlabel('Time')
        plt.ylabel('Volume')
        
        # Format x-axis
        plt.xticks(x, [hour.strftime('%Y-%m-%d\n%H:00') for hour in all_hours], rotation=45)
        
        # Add legend
        plt.legend()
        
        # Add grid for better readability
        plt.grid(True, alpha=0.3)
        
        # Adjust layout to prevent label cutoff
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
            logging.info(f"Plot saved to {save_path}")
        else:
            plt.show()
        
        plt.close()

"""
    * transaction volume
    * Number of unique senders
    * Average time between deposits
    * Forward destination analysis
    * Balance patterns
"""