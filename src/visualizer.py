from dash import Dash, dcc, html, dependencies
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_dash_app(order_book):
    """Create a Dash app to visualize the order book horizontally."""
    app = Dash(__name__)

    def create_figure(bids_df, asks_df):
        logger.info(f"Creating figure with {len(bids_df)} bids and {len(asks_df)} asks")
        logger.info(f"Bids sample: {bids_df.head().to_dict() if not bids_df.empty else 'Empty'}")
        logger.info(f"Asks sample: {asks_df.head().to_dict() if not asks_df.empty else 'Empty'}")
        fig = make_subplots(rows=1, cols=1, shared_yaxes=True, subplot_titles=["Order Book Depth"])

        # Scale quantities for visibility
        scale_factor = 50000  # Increased for thicker bars
        bids_quantities = bids_df["Quantity"] * scale_factor if not bids_df.empty else [0]
        asks_quantities = asks_df["Quantity"] * scale_factor if not asks_df.empty else [0]

        # Bids (buy orders, green, quantities to the left)
        fig.add_trace(
            go.Bar(
                y=bids_df["Price"] if not bids_df.empty else [0],
                x=[-x for x in bids_quantities],  # Negative for left side
                name="Bids",
                marker_color="green",
                opacity=0.7,
                orientation="h",
                width=1.0,  # Increased for thicker bars
            ),
            row=1,
            col=1,
        )

        # Asks (sell orders, red, quantities to the right)
        fig.add_trace(
            go.Bar(
                y=asks_df["Price"] if not asks_df.empty else [0],
                x=asks_quantities,
                name="Asks",
                marker_color="red",
                opacity=0.7,
                orientation="h",
                width=1.0,  # Increased for thicker bars
            ),
            row=1,
            col=1,
        )

        # Dynamic y-axis (price) range
        if not bids_df.empty and not asks_df.empty:
            mid_price = (bids_df["Price"].max() + asks_df["Price"].min()) / 2
            price_range = max(bids_df["Price"].max() - asks_df["Price"].min(), 1000)
            y_range = [mid_price - price_range / 2, mid_price + price_range / 2]
        else:
            y_range = [0, 1000]

        # Dynamic x-axis (quantity) range
        max_quantity = max(
            bids_df["Quantity"].max() * scale_factor if not bids_df.empty else 0,
            asks_df["Quantity"].max() * scale_factor if not asks_df.empty else 0,
            1,
        )

        fig.update_layout(
            title="Order Book for BTCUSDT (Horizontal)",
            yaxis_title="Price (USDT)",
            xaxis_title=f"Quantity (Scaled x{scale_factor})",
            showlegend=True,
            barmode="overlay",
            template="plotly_dark",
            yaxis=dict(tickformat=".2f", range=y_range, autorange=False),
            xaxis=dict(
                tickformat=".2f",
                range=[-max_quantity * 1.1, max_quantity * 1.1],
            ),
            height=800,
            margin=dict(l=50, r=50, t=100, b=50),
        )
        return fig

    # Wait for initial data (up to 15 seconds)
    logger.info("Waiting for initial WebSocket data")
    start_time = time.time()
    initial_bids_df, initial_asks_df = order_book.get_order_book()
    while initial_bids_df.empty and initial_asks_df.empty and time.time() - start_time < 15:
        time.sleep(0.5)
        initial_bids_df, initial_asks_df = order_book.get_order_book()
    logger.info(f"Initial order book: {len(initial_bids_df)} bids, {len(initial_asks_df)} asks")
    logger.info(f"Bids sample: {initial_bids_df.head().to_dict() if not initial_bids_df.empty else 'Empty'}")
    logger.info(f"Asks sample: {initial_asks_df.head().to_dict() if not initial_asks_df.empty else 'Empty'}")

    # Create initial figure
    initial_fig = create_figure(initial_bids_df, initial_asks_df)

    # Define layout with full-width and full-height styling
    app.layout = html.Div([
        dcc.Graph(
            id='order-book-graph',
            figure=initial_fig,
            style={'width': '100%', 'height': '100vh', 'margin': '0', 'padding': '0'},
            responsive=False,
        ),
        dcc.Interval(id='interval-component', interval=10*1000, n_intervals=0),
        html.Button("Refresh", id='refresh-button', n_clicks=0, style={'margin': '10px'}),
    ], style={'width': '100%', 'height': '100vh', 'margin': '0', 'padding': '0', 'display': 'flex', 'flexDirection': 'column'})

    @app.callback(
        dependencies.Output('order-book-graph', 'figure'),
        [dependencies.Input('interval-component', 'n_intervals'),
         dependencies.Input('refresh-button', 'n_clicks')],
    )
    def update_graph(n_intervals, n_clicks):
        logger.info(f"Callback triggered, n_intervals: {n_intervals}, n_clicks: {n_clicks}")
        bids_df, asks_df = order_book.get_order_book()
        logger.info(f"Updating graph: {len(bids_df)} bids, {len(asks_df)} asks")
        logger.info(f"Bids sample: {bids_df.head().to_dict() if not bids_df.empty else 'Empty'}")
        logger.info(f"Asks sample: {asks_df.head().to_dict() if not bids_df.empty else 'Empty'}")
        return create_figure(bids_df, asks_df)

    return app