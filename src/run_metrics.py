import logging
from scrapers.helpers.deposit_metrics import DepositMetrics
from main import Config
from utils.deposit_address_repository import DepositAddressRepository

def compute_metrics():
    deposit_data = deposit_metrics.deposit_data
    volumes, timeseries = deposit_metrics.aggregate_funding_volume(deposit_data)

    logging.info("="*20)
    logging.info("")
    logging.info(f"")
    logging.info(deposit_metrics.format_funding_volume(volumes))
    deposit_metrics.plot_time_series(timeseries, "time_series.png")
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