from collections import defaultdict
from datetime import datetime
import json
import logging
import statistics
from typing import Dict, List
from .data_classes import TransactionData
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import networkx as nx
import numpy as np

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
        deposit_mapping = {}
        
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

            timestamp = deposit['block_time']
            if 'sweep' in time_series_stats:
                if timestamp in time_series_stats['sweep']:
                    time_series_stats['sweep'][timestamp] += deposit['change']
                else:
                    time_series_stats['sweep'][timestamp] = deposit['change']
            else:
                time_series_stats['sweep'] = {
                    timestamp: deposit['change']
                }

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

            # Map deposit wallets to their funding wallets
            deposit_wallet = deposit['deposit_wallet']
            funding_wallets = [funding_tx['wallet'] for funding_tx in deposit['funding_data']]
            if deposit_wallet in deposit_mapping:
                deposit_mapping[deposit_wallet] = list(set(deposit_mapping[deposit_wallet] + funding_wallets))
            else:
                deposit_mapping[deposit_wallet] = list(set(funding_wallets))
        return aggregated_stats, time_series_stats, deposit_mapping


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

    def plot_wallet_network(self, deposit_mapping: Dict[str, List[str]], top_deposits: List[dict], save_path: str = None, max_nodes: int = 20):
        """
        Creates a network visualization of deposit wallets and their funding addresses.
        
        Args:
            deposit_mapping: Dictionary mapping deposit wallets to lists of funding wallets
            top_deposits: List of top deposits to prioritize in visualization
            save_path: Optional path to save the plot. If None, displays the plot
            max_nodes: Maximum number of deposit wallets to display to prevent overcrowding
        """
        # Create a new graph
        G = nx.Graph()
        
        # First, add nodes from top_deposits
        prioritized_wallets = [d['deposit_wallet'] for d in top_deposits]
        
        # Then add other wallets up to max_nodes
        remaining_slots = max_nodes - len(prioritized_wallets)
        if remaining_slots > 0:
            other_wallets = [w for w in deposit_mapping.keys() 
                            if w not in prioritized_wallets][:remaining_slots]
            deposit_wallets = prioritized_wallets + other_wallets
        else:
            deposit_wallets = prioritized_wallets[:max_nodes]
        
        # Add nodes and edges
        for deposit_wallet in deposit_wallets:
            if deposit_wallet not in deposit_mapping:
                continue
            
            # Add deposit wallet node with special color for top deposits
            is_top = deposit_wallet in prioritized_wallets
            G.add_node(deposit_wallet[:8] + "...", 
                       node_type="deposit",
                       is_top=is_top)  # Truncate address for readability
            
            # Add funding wallet nodes and edges
            for funding_wallet in deposit_mapping[deposit_wallet][:8]:  # Limit to 8 funding wallets per deposit
                funding_id = funding_wallet[:8] + "..."
                G.add_node(funding_id, node_type="funding")
                G.add_edge(deposit_wallet[:8] + "...", funding_id)
        
        plt.figure(figsize=(15, 10))
        
        # Create layout
        top_deposit_nodes = [node for node, attr in G.nodes(data=True) 
                            if attr.get("node_type") == "deposit" and attr.get("is_top")]
        other_deposit_nodes = [node for node, attr in G.nodes(data=True) 
                              if attr.get("node_type") == "deposit" and not attr.get("is_top")]
        funding_nodes = [node for node, attr in G.nodes(data=True) 
                        if attr.get("node_type") == "funding"]
        deposit_nodes = top_deposit_nodes + other_deposit_nodes
        pos = nx.circular_layout(G)  # Places nodes in a circle
        
        # Draw top deposit nodes in red
        nx.draw_networkx_nodes(G, pos, 
                              nodelist=top_deposit_nodes,
                              node_color='lightcoral',
                              node_size=1200,
                              alpha=0.7,
                              label='Top Deposit Addresses')
        
        # Draw other deposit nodes in blue
        nx.draw_networkx_nodes(G, pos, 
                              nodelist=other_deposit_nodes,
                              node_color='lightblue',
                              node_size=1000,
                              alpha=0.7,
                              label='Other Deposit Addresses')
        
        # Draw funding nodes in green
        nx.draw_networkx_nodes(G, pos,
                              nodelist=funding_nodes,
                              node_color='lightgreen',
                              node_size=700,
                              alpha=0.7,
                              label='User Funding Addresses')
        
        # Draw edges
        nx.draw_networkx_edges(G, pos, alpha=0.4)
        
        # Add labels
        nx.draw_networkx_labels(G, pos, font_size=8)
        
        plt.title('Wallet Relationship Network\n(Deposit Wallets and Their Funding Sources)')
        plt.legend()
        plt.axis('off')
        
        # Adjust layout to prevent label cutoff
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, bbox_inches='tight')
            logging.info(f"Network plot saved to {save_path}")
        else:
            plt.show()
        
        plt.close()

    def plot_top_deposits(self, top_deposits: List[dict], save_path: str = None):
        """
        Creates a bar chart of top deposits by volume.
        
        Args:
            top_deposits: List of deposit dictionaries sorted by change value
            save_path: Optional path to save the plot. If None, displays the plot
        """
        plt.figure(figsize=(15, 8))
        
        # Extract data for plotting
        wallets = [d['deposit_wallet'][:8] + "..." for d in top_deposits]  # Truncate for readability
        volumes = [d['change'] for d in top_deposits]
        colors = [plt.cm.viridis(i/len(top_deposits)) for i in range(len(top_deposits))]  # Color gradient
        
        # Create bar chart
        bars = plt.bar(range(len(wallets)), volumes, color=colors)
        
        # Customize the plot
        plt.title('Top Deposit Volumes by Wallet')
        plt.xlabel('Deposit Wallet Address')
        plt.ylabel('Volume')
        
        # Rotate x-axis labels for better readability
        plt.xticks(range(len(wallets)), wallets, rotation=45, ha='right')
        
        # Add value labels on top of each bar
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:,.0f}',
                    ha='center', va='bottom')
        
        # Add grid for better readability
        plt.grid(True, axis='y', alpha=0.3)
        
        # Adjust layout to prevent label cutoff
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, bbox_inches='tight')
            logging.info(f"Top deposits plot saved to {save_path}")
        else:
            plt.show()
        
        plt.close()
