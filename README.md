# Exchange Scraper

Scrapes for exchange deposit addresses on Solana and Ethereum.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/caronsch/exchange-scraper.git
cd exchange-scraper
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create your configuration file:
```bash
cp config.yaml.template config.yaml
```

Edit `config.yaml` with your specific settings, specifically at which slot to start scraping, the distance to scrape, and the tokens to scrape.

Example config.yaml:
```
solana:
  start_block: 315053829 
  blocks_to_parse: 1000
  url: "https://svc.blockdaemon.com/solana/mainnet/native"
  api_key: "<API_KEY>"
  api_type: "bearer"
  rps_limit: 5
  tokens:
    - ticker: TRUMP
      address: "6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN"
    - ticker: USDC
      address: "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    - ticker: USDT
      address: "Es9vMFrzaCERmJfrF4H2FYD4KCo4Zxj8vjPPVBRdYxU"
```

Set known exchange hot wallets in `hot_wallets.yaml`.
```
ethereum:
  coinbase:
    - "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    - "0x123d35Cc6634C0532925a3b844Bc454e4438f789"
  binance:
    - "0x987d35Cc6634C0532925a3b844Bc454e4438fabc"
    - "0x456d35Cc6634C0532925a3b844Bc454e4438fdef"

solana:
  coinbase:
    - "H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS"
    - "2AQdpHJ2JpcEgPiATUXjQxA8QmafFegfQwSLWSprPicm"
    - "GJRs4FwHtemZ5ZE9x3FNvJ8TMwitKTh21yxdRPqn7npE"
  binance:
    - "2ojv9BAiHUrvsm9gxDe7fJSzbNZSJcxZvf8dqmWGHG8S"
    - "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9" 
    - "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
```

## Usage

To collect new deposit addresses:
```bash
    python src/main.py
```

To only run the metrics computation using the existing json data in `data/`:
```bash
python src/run_metrics.py
```

To run the tests:
```bash
python -m pytest tests/
```