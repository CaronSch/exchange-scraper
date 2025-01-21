import logging
from scrapers.helpers.deposit_metrics import DepositMetrics
from main import Config
from utils.deposit_address_repository import DepositAddressRepository

def compute_metrics():
    # Sort deposit data by 'change' value in descending order
    sorted_deposits = sorted(deposit_metrics.deposit_data, 
                           key=lambda x: x.get('change', 0), 
                           reverse=True)
    
    # Get top 10 deposits
    top_deposits = sorted_deposits[:10]
    
    logging.info("Top 10 deposits by volume:")
    for i, deposit in enumerate(top_deposits, 1):
        logging.info(f"{i}. Wallet: {deposit['deposit_wallet']}, "
                    f"Volume: {deposit['change']:.2f} {deposit['token_info']['ticker']}, "
                    f"Exchange: {deposit['token_info']['exchange']}")

    volumes, timeseries, deposit_mapping = deposit_metrics.aggregate_funding_volume(deposit_metrics.deposit_data)

    # Create bar chart of top deposits
    deposit_metrics.plot_top_deposits(top_deposits, save_path="top_deposits.png")
    logging.info("Created top deposits plot `top_deposits.png`")

    logging.info(deposit_metrics.format_funding_volume(volumes))
    deposit_metrics.plot_time_series(timeseries, "time_series.png")
    logging.info("Created time series plot `time_series.png`")

    deposit_metrics.plot_wallet_network(deposit_mapping, save_path="wallet_network.png")
    logging.info("Created wallet network plot `wallet_network.png`")

if __name__ == "__main__":
    config = Config()

    config = Config()
    logging.basicConfig(
        level=config.config["logging"]["level"],
        filename=config.config["logging"]["file"],
        format=config.config["logging"]["format"],
        datefmt=config.config["logging"]["datefmt"]
    )
    logging.info("Application started")

    deposit_repo = DepositAddressRepository(config.config["storage"]["deposit_addresses_path"])
    deposit_metrics = DepositMetrics()
    file_path = deposit_repo.get_latest_deposit_file()
    deposit_metrics.load_deposit_data(file_path)
    compute_metrics()