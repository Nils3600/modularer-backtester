# chartplotter.py

import plotly.graph_objects as go
import plotly.io as pio

class ChartPlotter:
    def __init__(self, df, trades):
        self.df = df
        self.trades = trades
    
    def plot_trades_plotly(self, price_field="Close", title="Trades mit Plotly"):
        
        trades = self.trades
        fig = go.Figure()
        
        # Preislinie (z. B. Close)
        fig.add_trace(go.Scatter(
            x=self.df.index,
            y=self.df[price_field],
            mode="lines",
            name="Preis",
            line=dict(color="black", width=3) # von 1 zu 3 geändert
        ))
    
        for idx, trade in enumerate(trades):
            entry_time = trade["entry_time"]
            exit_time = trade["exit_time"]
            entry_price = trade["entry_price"]
            exit_price = trade["exit_price"]
            
            # print(trade)
            # print(trade['pnl'])
            # input('Pause')
            pnl = trade["pnl"]
            color = "green" if pnl >= 0 else "red"
    
            # Einstiegspunkt
            fig.add_trace(go.Scatter(
                x=[entry_time],
                y=[entry_price],
                mode="markers+text",
                name="Entry",
                #text=[f'{trade["id"]}<br>Entry'],
                marker=dict(symbol="triangle-up", size=10, color=color),
                textposition="bottom center"
            ))
    
            # Ausstiegspunkt
            fig.add_trace(go.Scatter(
                x=[exit_time],
                y=[exit_price],
                mode="markers+text",
                name="Exit",
                #text=[f'{trade["id"]}<br>Exit<br>PNL: {trade["pnl"]:.2f}'],
                marker=dict(symbol="triangle-down", size=10, color=color),
                textposition="top center"
            ))
    
            pnl = trade["pnl"]
            line_color = "green" if pnl >= 0 else "red"
        
            # Verbindungslinie
            fig.add_trace(go.Scatter(
                x=[trade["entry_time"], trade["exit_time"]],
                y=[trade["entry_price"], trade["exit_price"]],
                mode="lines",
                line=dict(color=line_color, dash="dot", width=2),
                showlegend=False,
                hoverinfo="skip"
            ))
    
        fig.update_layout(
            title=title,
            xaxis_title="Zeit",
            yaxis_title="Preis",
            hovermode="x unified",
            legend_title="Legende",
            template="plotly_white"
        )
        
        fig.write_html("trades_plot.html")
        pio.renderers.default = "browser"
        fig.show()
    

    def plot_trades_2(self, entry_mgr=None, show_equity=True):
        
        df = self.df
        trades = self.trades
        
        fig = go.Figure()
    
        # 📉 Kurslinie
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Close"],
            mode="lines",
            name="Close",
            line=dict(color="black", width=1)
        ))
    
        # 📍 Entry/Exit Punkte + Verbindung
        for t in trades:
            color = "green" if t["pnl"] > 0 else "red"
    
            fig.add_trace(go.Scatter(
                x=[t["entry_time"], t["exit_time"]],
                y=[t["entry_price"], t["exit_price"]],
                mode="lines+markers",
                line=dict(color=color, width=2),
                marker=dict(symbol="circle", size=8, color=color),
                name=t["id"],
                hovertemplate=(
                    f"<b>{t['id']}</b><br>"
                    f"Typ: {t['type'].upper()}<br>"
                    f"Entry: {t['entry_price']}<br>"
                    f"Exit: {t['exit_price']}<br>"
                    f"PnL: {t['pnl']}<br>"
                    #f"Return: {t['return_pct']}%<br>"
                    f"Grund: {t['exit_reason'].upper()}"
                )
            ))
    
        # ⛔ Geblockte Einstiege (wenn vorhanden)
        # if entry_mgr:
        #     blocked_markers = entry_mgr.to_plotly_markers(y_level=df["Close"])
        #     fig.add_traces(blocked_markers)
    
        # 💰 Optionale Equity-Kurve
        if show_equity:
            equity = [0]
            for t in trades:
                equity.append(equity[-1] + t["pnl"])
            equity = equity[1:]
            times = [t["exit_time"] for t in trades]
    
            fig.add_trace(go.Scatter(
                x=times, y=equity,
                mode="lines",
                line=dict(color="royalblue", dash="dot"),
                name="Equity",
                yaxis="y2"
            ))
    
            fig.update_layout(
                yaxis2=dict(
                    overlaying="y",
                    side="right",
                    title="Equity",
                    showgrid=False
                )
            )
    
        fig.update_layout(
            title="📊 Trades & Signale (inkl. blockierter Einstiege)",
            xaxis_title="Zeit",
            yaxis_title="Preis",
            template="plotly_white",
            legend=dict(orientation="h", y=-0.2),
            height=600
        )
    
        fig.write_html("trade2_plot.html")
        pio.renderers.default = "browser"
        fig.show()
        
        
