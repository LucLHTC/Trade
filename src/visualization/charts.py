"""
Advanced chart visualizations for trading system.
Creates TradingView-style charts with indicators and signals.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from typing import Optional, List, Dict, Any

from src.common.logger import get_logger

logger = get_logger(__name__)


def create_live_price_chart(
    candles_df: pd.DataFrame,
    indicators: Optional[List[str]] = None,
    predictions_df: Optional[pd.DataFrame] = None,
    height: int = 800,
) -> go.Figure:
    """
    Create interactive candlestick chart with technical indicators and model signals.

    Args:
        candles_df: DataFrame with OHLCV data and indicators
        indicators: List of indicators to display
        predictions_df: DataFrame with model predictions
        height: Chart height in pixels

    Returns:
        Plotly figure
    """
    if candles_df.empty:
        # Return empty chart
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
        return fig

    # Default indicators
    if indicators is None:
        indicators = ["ema_20", "ema_50", "rsi_14", "macd", "bb_upper", "bb_lower"]

    # Determine number of subplots
    has_rsi = any("rsi" in ind for ind in indicators)
    has_macd = any("macd" in ind for ind in indicators)

    row_heights = [0.6]  # Main chart
    subplot_titles = ["Price Chart"]

    if has_rsi:
        row_heights.append(0.2)
        subplot_titles.append("RSI")
    if has_macd:
        row_heights.append(0.2)
        subplot_titles.append("MACD")

    # Create subplots
    fig = make_subplots(
        rows=len(row_heights),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        subplot_titles=subplot_titles,
    )

    # 1. Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=candles_df.index,
            open=candles_df["open"],
            high=candles_df["high"],
            low=candles_df["low"],
            close=candles_df["close"],
            name="Price",
            increasing_line_color="rgb(38,166,154)",
            decreasing_line_color="rgb(239,83,80)",
        ),
        row=1,
        col=1,
    )

    # 2. Moving Averages
    if "ema_20" in candles_df.columns and "ema_20" in indicators:
        fig.add_trace(
            go.Scatter(
                x=candles_df.index,
                y=candles_df["ema_20"],
                mode="lines",
                name="EMA 20",
                line=dict(color="rgba(255,165,0,0.8)", width=1),
            ),
            row=1,
            col=1,
        )

    if "ema_50" in candles_df.columns and "ema_50" in indicators:
        fig.add_trace(
            go.Scatter(
                x=candles_df.index,
                y=candles_df["ema_50"],
                mode="lines",
                name="EMA 50",
                line=dict(color="rgba(0,150,255,0.8)", width=1),
            ),
            row=1,
            col=1,
        )

    # 3. Bollinger Bands
    if (
        "bb_upper" in candles_df.columns
        and "bb_lower" in candles_df.columns
        and "bb_upper" in indicators
    ):
        fig.add_trace(
            go.Scatter(
                x=candles_df.index,
                y=candles_df["bb_upper"],
                mode="lines",
                name="BB Upper",
                line=dict(color="rgba(150,150,150,0.5)", width=1, dash="dash"),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=candles_df.index,
                y=candles_df["bb_lower"],
                mode="lines",
                name="BB Lower",
                line=dict(color="rgba(150,150,150,0.5)", width=1, dash="dash"),
                fill="tonexty",
                fillcolor="rgba(150,150,150,0.1)",
            ),
            row=1,
            col=1,
        )

    # 4. Model Predictions (if available)
    if predictions_df is not None and not predictions_df.empty:
        # Long signals
        long_signals = predictions_df[predictions_df["prediction"] == 1]
        if not long_signals.empty:
            fig.add_trace(
                go.Scatter(
                    x=long_signals["timestamp"],
                    y=candles_df.loc[long_signals["timestamp"], "low"] * 0.9995,
                    mode="markers",
                    name="Long Signal",
                    marker=dict(
                        symbol="triangle-up",
                        size=12,
                        color="green",
                        line=dict(color="darkgreen", width=1),
                    ),
                    hovertemplate="<b>LONG</b><br>"
                    + "Time: %{x}<br>"
                    + "Confidence: %{customdata:.2%}<extra></extra>",
                    customdata=long_signals["confidence_long"],
                ),
                row=1,
                col=1,
            )

        # Short signals
        short_signals = predictions_df[predictions_df["prediction"] == -1]
        if not short_signals.empty:
            fig.add_trace(
                go.Scatter(
                    x=short_signals["timestamp"],
                    y=candles_df.loc[short_signals["timestamp"], "high"] * 1.0005,
                    mode="markers",
                    name="Short Signal",
                    marker=dict(
                        symbol="triangle-down",
                        size=12,
                        color="red",
                        line=dict(color="darkred", width=1),
                    ),
                    hovertemplate="<b>SHORT</b><br>"
                    + "Time: %{x}<br>"
                    + "Confidence: %{customdata:.2%}<extra></extra>",
                    customdata=short_signals["confidence_short"],
                ),
                row=1,
                col=1,
            )

    # 5. RSI Subplot
    current_row = 2
    if has_rsi and "rsi_14" in candles_df.columns:
        fig.add_trace(
            go.Scatter(
                x=candles_df.index,
                y=candles_df["rsi_14"],
                mode="lines",
                name="RSI",
                line=dict(color="purple", width=1.5),
            ),
            row=current_row,
            col=1,
        )

        # RSI reference lines
        fig.add_hline(
            y=70,
            line_dash="dash",
            line_color="red",
            opacity=0.5,
            row=current_row,
            col=1,
        )
        fig.add_hline(
            y=30,
            line_dash="dash",
            line_color="green",
            opacity=0.5,
            row=current_row,
            col=1,
        )
        fig.update_yaxes(range=[0, 100], row=current_row, col=1)

        current_row += 1

    # 6. MACD Subplot
    if has_macd and "macd" in candles_df.columns:
        fig.add_trace(
            go.Scatter(
                x=candles_df.index,
                y=candles_df["macd"],
                mode="lines",
                name="MACD",
                line=dict(color="blue", width=1.5),
            ),
            row=current_row,
            col=1,
        )

        if "macd_signal" in candles_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=candles_df.index,
                    y=candles_df["macd_signal"],
                    mode="lines",
                    name="Signal",
                    line=dict(color="orange", width=1.5),
                ),
                row=current_row,
                col=1,
            )

        if "macd_hist" in candles_df.columns:
            colors = [
                "green" if val >= 0 else "red" for val in candles_df["macd_hist"]
            ]
            fig.add_trace(
                go.Bar(
                    x=candles_df.index,
                    y=candles_df["macd_hist"],
                    name="Histogram",
                    marker_color=colors,
                    opacity=0.5,
                ),
                row=current_row,
                col=1,
            )

        fig.add_hline(y=0, line_dash="dash", line_color="gray", row=current_row, col=1)

    # Layout
    fig.update_layout(
        title="EUR/USD Live Trading Chart",
        xaxis_rangeslider_visible=False,
        height=height,
        hovermode="x unified",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_dark",
    )

    fig.update_xaxes(title_text="Time", row=len(row_heights), col=1)
    fig.update_yaxes(title_text="Price", row=1, col=1)

    return fig


def create_backtest_chart(
    candles_df: pd.DataFrame,
    trades_df: pd.DataFrame,
    equity_curve: Optional[pd.DataFrame] = None,
    height: int = 1000,
) -> go.Figure:
    """
    Create backtest visualization with entry/exit markers and equity curve.

    Args:
        candles_df: DataFrame with OHLCV data
        trades_df: DataFrame with trade history
        equity_curve: DataFrame with equity over time
        height: Chart height in pixels

    Returns:
        Plotly figure
    """
    if candles_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No backtest data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
        return fig

    # Create subplots
    row_heights = [0.6, 0.4] if equity_curve is not None else [1.0]
    subplot_titles = (
        ["Price Chart with Trades", "Equity Curve"]
        if equity_curve is not None
        else ["Price Chart with Trades"]
    )

    fig = make_subplots(
        rows=len(row_heights),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=row_heights,
        subplot_titles=subplot_titles,
    )

    # 1. Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=candles_df.index,
            open=candles_df["open"],
            high=candles_df["high"],
            low=candles_df["low"],
            close=candles_df["close"],
            name="Price",
            increasing_line_color="rgb(38,166,154)",
            decreasing_line_color="rgb(239,83,80)",
        ),
        row=1,
        col=1,
    )

    if not trades_df.empty:
        # 2. Entry markers
        long_entries = trades_df[trades_df["direction"] == 1]
        short_entries = trades_df[trades_df["direction"] == -1]

        if not long_entries.empty:
            fig.add_trace(
                go.Scatter(
                    x=long_entries["entry_time"],
                    y=long_entries["entry_price"],
                    mode="markers",
                    name="Long Entry",
                    marker=dict(
                        symbol="triangle-up",
                        size=15,
                        color="lime",
                        line=dict(color="darkgreen", width=2),
                    ),
                    hovertemplate="<b>LONG ENTRY</b><br>"
                    + "Time: %{x}<br>"
                    + "Price: %{y:.5f}<br>"
                    + "Size: %{customdata[0]:.2f}<br>"
                    + "Risk: $%{customdata[1]:.2f}<extra></extra>",
                    customdata=np.column_stack(
                        (long_entries["position_size"], long_entries["risk_amount"])
                    ),
                ),
                row=1,
                col=1,
            )

        if not short_entries.empty:
            fig.add_trace(
                go.Scatter(
                    x=short_entries["entry_time"],
                    y=short_entries["entry_price"],
                    mode="markers",
                    name="Short Entry",
                    marker=dict(
                        symbol="triangle-down",
                        size=15,
                        color="orange",
                        line=dict(color="darkred", width=2),
                    ),
                    hovertemplate="<b>SHORT ENTRY</b><br>"
                    + "Time: %{x}<br>"
                    + "Price: %{y:.5f}<br>"
                    + "Size: %{customdata[0]:.2f}<br>"
                    + "Risk: $%{customdata[1]:.2f}<extra></extra>",
                    customdata=np.column_stack(
                        (short_entries["position_size"], short_entries["risk_amount"])
                    ),
                ),
                row=1,
                col=1,
            )

        # 3. Exit markers
        winning_exits = trades_df[trades_df["pnl"] > 0]
        losing_exits = trades_df[trades_df["pnl"] <= 0]

        if not winning_exits.empty:
            fig.add_trace(
                go.Scatter(
                    x=winning_exits["exit_time"],
                    y=winning_exits["exit_price"],
                    mode="markers+text",
                    name="Winning Exit",
                    marker=dict(symbol="circle", size=12, color="green"),
                    text=winning_exits["exit_reason"].str[:2].str.upper(),
                    textposition="top center",
                    textfont=dict(size=8, color="white"),
                    hovertemplate="<b>EXIT (Win)</b><br>"
                    + "Time: %{x}<br>"
                    + "Price: %{y:.5f}<br>"
                    + "Reason: %{customdata[0]}<br>"
                    + "P&L: $%{customdata[1]:+.2f} (%{customdata[2]:+.2f}%)<br>"
                    + "Hold: %{customdata[3]:.1f}h<extra></extra>",
                    customdata=np.column_stack(
                        (
                            winning_exits["exit_reason"],
                            winning_exits["pnl"],
                            winning_exits["pnl_pct"],
                            winning_exits["holding_hours"],
                        )
                    ),
                ),
                row=1,
                col=1,
            )

        if not losing_exits.empty:
            fig.add_trace(
                go.Scatter(
                    x=losing_exits["exit_time"],
                    y=losing_exits["exit_price"],
                    mode="markers+text",
                    name="Losing Exit",
                    marker=dict(symbol="circle", size=12, color="red"),
                    text=losing_exits["exit_reason"].str[:2].str.upper(),
                    textposition="bottom center",
                    textfont=dict(size=8, color="white"),
                    hovertemplate="<b>EXIT (Loss)</b><br>"
                    + "Time: %{x}<br>"
                    + "Price: %{y:.5f}<br>"
                    + "Reason: %{customdata[0]}<br>"
                    + "P&L: $%{customdata[1]:+.2f} (%{customdata[2]:+.2f}%)<br>"
                    + "Hold: %{customdata[3]:.1f}h<extra></extra>",
                    customdata=np.column_stack(
                        (
                            losing_exits["exit_reason"],
                            losing_exits["pnl"],
                            losing_exits["pnl_pct"],
                            losing_exits["holding_hours"],
                        )
                    ),
                ),
                row=1,
                col=1,
            )

        # 4. Draw trade lines (entry to exit)
        for _, trade in trades_df.iterrows():
            color = "rgba(0,255,0,0.3)" if trade["pnl"] > 0 else "rgba(255,0,0,0.3)"
            fig.add_shape(
                type="line",
                x0=trade["entry_time"],
                y0=trade["entry_price"],
                x1=trade["exit_time"],
                y1=trade["exit_price"],
                line=dict(color=color, width=2),
                row=1,
                col=1,
            )

    # 5. Equity Curve
    if equity_curve is not None and not equity_curve.empty:
        fig.add_trace(
            go.Scatter(
                x=equity_curve.index,
                y=equity_curve["equity"],
                mode="lines",
                name="Equity",
                line=dict(color="cyan", width=2),
                fill="tozeroy",
                fillcolor="rgba(0,255,255,0.1)",
            ),
            row=2,
            col=1,
        )

        # Add drawdown shading
        peak = equity_curve["equity"].expanding().max()
        drawdown = (equity_curve["equity"] - peak) / peak * 100

        fig.add_trace(
            go.Scatter(
                x=equity_curve.index,
                y=drawdown,
                mode="lines",
                name="Drawdown %",
                line=dict(color="red", width=1),
                fill="tozeroy",
                fillcolor="rgba(255,0,0,0.2)",
                yaxis="y3",
            ),
            row=2,
            col=1,
        )

        # Secondary y-axis for drawdown
        fig.update_yaxes(title_text="Equity ($)", row=2, col=1)

    # Layout
    fig.update_layout(
        title="Backtest Results",
        xaxis_rangeslider_visible=False,
        height=height,
        hovermode="x unified",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_dark",
    )

    fig.update_xaxes(title_text="Time", row=len(row_heights), col=1)
    fig.update_yaxes(title_text="Price", row=1, col=1)

    return fig


def create_equity_curve_chart(
    equity_df: pd.DataFrame, trades_df: Optional[pd.DataFrame] = None, height: int = 500
) -> go.Figure:
    """
    Create standalone equity curve chart.

    Args:
        equity_df: DataFrame with equity over time
        trades_df: Optional trades for marking on curve
        height: Chart height

    Returns:
        Plotly figure
    """
    fig = go.Figure()

    # Equity line
    fig.add_trace(
        go.Scatter(
            x=equity_df.index,
            y=equity_df["equity"],
            mode="lines",
            name="Equity",
            line=dict(color="cyan", width=3),
            fill="tozeroy",
            fillcolor="rgba(0,255,255,0.2)",
        )
    )

    # Mark trades if provided
    if trades_df is not None and not trades_df.empty:
        # Calculate equity at each trade exit
        initial_equity = equity_df["equity"].iloc[0]
        trade_equities = []
        cumulative_pnl = 0

        for _, trade in trades_df.iterrows():
            cumulative_pnl += trade["pnl"]
            trade_equities.append(initial_equity + cumulative_pnl)

        winning_trades = trades_df[trades_df["pnl"] > 0]
        losing_trades = trades_df[trades_df["pnl"] <= 0]

        if not winning_trades.empty:
            win_indices = winning_trades.index
            win_equities = [trade_equities[i] for i in win_indices]
            fig.add_trace(
                go.Scatter(
                    x=winning_trades["exit_time"],
                    y=win_equities,
                    mode="markers",
                    name="Wins",
                    marker=dict(symbol="circle", size=8, color="green"),
                )
            )

        if not losing_trades.empty:
            loss_indices = losing_trades.index
            loss_equities = [trade_equities[i] for i in loss_indices]
            fig.add_trace(
                go.Scatter(
                    x=losing_trades["exit_time"],
                    y=loss_equities,
                    mode="markers",
                    name="Losses",
                    marker=dict(symbol="circle", size=8, color="red"),
                )
            )

    fig.update_layout(
        title="Equity Curve",
        xaxis_title="Time",
        yaxis_title="Equity ($)",
        height=height,
        hovermode="x unified",
        template="plotly_dark",
    )

    return fig
