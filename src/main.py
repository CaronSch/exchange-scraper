import yaml
import logging
from pathlib import Path
from utils.deposit_address_repository import DepositAddressRepository
from utils.address_loader import get_exchange_hot_wallets
from scrapers.evm_scraper import EVMScraper
from scrapers.solana_scraper import SolanaScraper


class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
            
        with open(self.config_path) as f:
            return yaml.safe_load(f)

def main():
    """Main entry point for the application."""
    try:
        config = Config()
        logging.basicConfig(
            level=config.config["logging"]["level"],
            filename=config.config["logging"]["file"],
            format=config.config["logging"]["format"],
            datefmt=config.config["logging"]["datefmt"]
        )
        logging.info("Application started")

        # Initialize scrapers
        # eth_wallets = get_exchange_hot_wallets('ethereum')
        sol_wallets = get_exchange_hot_wallets('solana')

        # Pass config and specify which EVM chain to use
        # eth_scraper = EVMScraper(eth_wallets, 'ethereum', config.config)
        # pol_scraper = EVMScraper(eth_wallets, 'polygon', config.config)
        sol_scraper = SolanaScraper(sol_wallets, config.config, logging)

        # Connect to nodes
        # eth_scraper.connect()
        # pol_scraper.connect()
        sol_scraper.connect()

        # Get latest transactions
        # eth_transactions = eth_scraper.get_latest_transactions()
        # slot = self.client.get_slot().value 
        sol_scraper.parse_blocks()

        # Initialize repository and store deposit addresses
        deposit_repo = DepositAddressRepository(config.config["storage"]["deposit_addresses_path"])
        deposit_data = deposit_repo.save_deposit_addresses(sol_scraper.potential_deposit_addresses)
            
        # logging.info(f"Found {len(eth_transactions)} Ethereum transactions")
        logging.info(f"Found {len(sol_scraper.potential_deposit_addresses)} potential Solana deposit addresses")

        # Compute metrics
        sol_scraper.metrics.compute_metrics(deposit_data)

        logging.info("Application finished")
        
    except Exception as e:
        logging.error(f"Error starting application: {e}")
        raise

if __name__ == "__main__":
    main()