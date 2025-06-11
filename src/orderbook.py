from pybit.unified_trading import WebSocket
import pandas as pd
from time import sleep
import logging
from threading import Lock

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BybitOrderBook:
    def __init__(self, symbol="BTCUSDT", depth=50, testnet=True):
        self.symbol = symbol
        self.depth = depth
        self.testnet = testnet
        self.order_book = {"bids": [], "asks": []}
        self.lock = Lock()  # Add thread lock
        self.ws = WebSocket(testnet=self.testnet, channel_type="linear")
        logger.info(f"Initialized BybitOrderBook for {symbol} with depth {depth}, testnet={testnet}")

    def handle_message(self, message):
        """Process WebSocket messages."""
        logger.info(f"Received WebSocket message: {message}")
        data = message.get("data", {})
        if not data:
            logger.warning("Empty data in message")
            return

        with self.lock:  # Protect order_book updates
            if message.get("type") == "snapshot":
                self.order_book["bids"] = [[float(price), float(quantity)] for price, quantity in data.get("b", [])]
                self.order_book["asks"] = [[float(price), float(quantity)] for price, quantity in data.get("a", [])]
            elif message.get("type") == "delta":
                self._update_order_book(data.get("b", []), data.get("a", []))
            else:
                logger.warning(f"Unknown message type: {message.get('type')}")

        logger.info(f"Updated order book: {len(self.order_book['bids'])} bids, {len(self.order_book['asks'])} asks")

    def _update_order_book(self, bids, asks):
        """Apply delta updates to the order book."""
        with self.lock:
            for price, quantity in bids:
                price = float(price)
                quantity = float(quantity)
                self._update_side("bids", price, quantity)

            for price, quantity in asks:
                price = float(price)
                quantity = float(quantity)
                self._update_side("asks", price, quantity)

    def _update_side(self, side, price, quantity):
        """Update a single side (bids or asks) of the order book."""
        book_side = self.order_book[side]
        for i, [existing_price, _] in enumerate(book_side):
            if existing_price == price:
                if quantity == 0:
                    book_side.pop(i)
                else:
                    book_side[i] = [price, quantity]
                break
        else:
            if quantity > 0:
                book_side.append([price, quantity])

        self.order_book[side] = sorted(book_side, key=lambda x: x[0], reverse=(side == "bids"))
        self.order_book[side] = self.order_book[side][:self.depth]

    def start(self):
        """Start the WebSocket stream."""
        try:
            self.ws.orderbook_stream(depth=self.depth, symbol=self.symbol, callback=self.handle_message)
            logger.info(f"Started WebSocket for {self.symbol} with depth {self.depth}")
            while True:
                sleep(1)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            raise

    def get_order_book(self):
        """Return the current order book as a pandas DataFrame."""
        with self.lock:
            bids_df = pd.DataFrame(self.order_book["bids"], columns=["Price", "Quantity"])
            asks_df = pd.DataFrame(self.order_book["asks"], columns=["Price", "Quantity"])
            logger.info(f"Returning order book: {len(bids_df)} bids, {len(asks_df)} asks")
            return bids_df, asks_df
