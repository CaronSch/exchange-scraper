import yaml
from pathlib import Path

def load_addresses():
    address_file = Path("hot_wallets.yaml")
    with open(address_file, "r") as f:
        return yaml.safe_load(f)

def get_exchange_hot_wallets(chain: str) -> dict[str,list[str]]:
    """
    Get hot wallets for a specific blockchain and exchange
    
    Args:
        chain: 'ethereum' or 'solana'
    
    Returns:
        Dictionary of exchanges mapped to list of addresses
    """
    addresses = load_addresses()
    return addresses[chain]