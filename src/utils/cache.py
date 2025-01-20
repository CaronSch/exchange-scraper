import json
from pathlib import Path
from typing import Dict, Any, Callable
from datetime import datetime, timedelta
from functools import wraps

class TransactionCache:
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def get_cache_file(self, chain: str, address: str) -> Path:
        """Generate cache filename for chain/address combination"""
        return self.cache_dir / f"{chain}_{address}.json"
    
    def read_cache(self, chain: str, address: str) -> Dict[str, Any]:
        """Read cached transactions for an address"""
        cache_file = self.get_cache_file(chain, address)
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)
        return {'last_updated': None, 'transactions': {}}
    
    def write_cache(self, chain: str, address: str, transactions: Dict[str, Any]) -> None:
        """Write transactions to cache"""
        cache_file = self.get_cache_file(chain, address)
        cache_data = {
            'last_updated': datetime.now().isoformat(),
            'transactions': transactions
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)

def cache_transactions(cache_duration: timedelta = timedelta(hours=1)):
    """
    Decorator to cache transactions for a specified duration
    
    Args:
        cache_duration: How long to consider cached data valid
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(scraper, *args, **kwargs):
            cache = TransactionCache()
            
            # Check cache for each address
            all_transactions = []
            needs_update = False
            
            for address in scraper.addresses:
                cached_data = cache.read_cache(scraper.chain_type, address)
                last_updated = cached_data.get('last_updated')
                
                if last_updated is None:
                    needs_update = True
                    continue
                    
                last_updated = datetime.fromisoformat(last_updated)
                if datetime.now() - last_updated > cache_duration:
                    needs_update = True
                    continue
                    
                # Use cached transactions if they're still valid
                all_transactions.extend(cached_data['transactions'].values())
            
            # If cache is invalid or missing, fetch new data
            if needs_update:
                new_transactions = func(scraper, *args, **kwargs)
                
                # Group transactions by address for caching
                by_address: Dict[str, Dict[str, Any]] = {}
                for tx in new_transactions:
                    for address in scraper.addresses:
                        if address in (tx['from'], tx['to']):
                            if address not in by_address:
                                by_address[address] = {}
                            by_address[address][tx['hash']] = tx
                
                # Update cache for each address
                for address, transactions in by_address.items():
                    cache.write_cache(scraper.chain_type, address, transactions)
                
                return new_transactions
            
            return all_transactions
            
        return wrapper
    return decorator 