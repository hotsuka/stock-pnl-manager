import sys
import logging
from app import create_app
from app.services.stock_price_fetcher import StockPriceFetcher
from app.models.holding import Holding

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = create_app()

def debug_update():
    with app.app_context():
        holdings = Holding.query.all()
        logger.info(f"Found {len(holdings)} holdings in database.")
        
        for holding in holdings:
            logger.info(f"Checking ticker: {holding.ticker_symbol}")
            
            # 1. Try format
            yf_ticker = StockPriceFetcher._format_ticker(holding.ticker_symbol)
            logger.info(f"  Formatted ticker: {yf_ticker}")
            
            # 2. Try fetch directly
            data = StockPriceFetcher.get_current_price(holding.ticker_symbol, use_cache=False)
            
            if data:
                logger.info(f"  Success! Price: {data['price']} {data['currency']}")
            else:
                logger.error(f"  Failed to fetch price for {holding.ticker_symbol}")
                
        # 3. Run full update
        logger.info("Running bulk update...")
        results = StockPriceFetcher.update_all_holdings_prices()
        logger.info(f"Update results: {results}")

if __name__ == "__main__":
    debug_update()
