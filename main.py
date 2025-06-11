from src.orderbook import BybitOrderBook
from src.visualizer import create_dash_app
import threading

def main():
    # Initialize order book for BTCUSDT with depth 50 (use testnet=True for testing)
    order_book = BybitOrderBook(symbol="BTCUSDT", depth=50, testnet=True)

    # Start WebSocket in a separate thread
    threading.Thread(target=order_book.start, daemon=True).start()

    # Create and run Dash app
    app = create_dash_app(order_book)
    app.run_server(debug=True, port=8050)

if __name__ == "__main__":
    main()