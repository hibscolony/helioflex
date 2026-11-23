from html import escape
import plotly.express as px
import streamlit as st

COLORS = ["#d78908", "#087d73", "#5478bc", "#8466ae"]


def header(section, title, description):
    st.html(
        f"""
    <style>
    .hf-banner {{position:relative;isolation:isolate;overflow:hidden;border-radius:22px;
    background:#064a43;color:white;padding:clamp(22px,4vw,48px);margin-bottom:8px}}
    .hf-banner h1 {{color:#fff;font:700 clamp(1.65rem,3.8vw,3rem)/1.1 system-ui;
    max-width:74%;margin:0;letter-spacing:-.045em;padding:0}}
    .hf-banner small {{color:#bcf1da;display:block;margin-top:10px}}
    .hf-banner:before {{content:"";position:absolute;z-index:-1;right:6%;top:-34px;
    border-radius:100%;background:#ffcc53;width:105px;height:105px}}
    .hf-banner:after {{content:"";position:absolute;z-index:-1;right:-22px;bottom:-40px;
    width:26%;height:105px;transform:skew(-28deg) rotate(-10deg);border:3px solid #88d4c5;
    background-color:#247c79;background-image:linear-gradient(#80c3b9 1px,transparent 1px),
    linear-gradient(90deg,#80c3b9 1px,transparent 1px);background-size:32px 22px}}
    .hf-grid {{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,195px),1fr));gap:12px}}
    .hf-card {{background:var(--wash);border-top:4px solid var(--accent);border-radius:14px;
    padding:16px 18px;color:#193631;min-width:0}}
    .hf-card strong {{display:block;font:bold clamp(1.15rem,2vw,1.7rem)/1.25 system-ui;
    margin:6px 0;letter-spacing:-.04em;overflow-wrap:anywhere}}
    .hf-card small {{color:#425d56}}
    </style>
    <header class="hf-banner"><h1>{escape(title)}</h1><small>{escape(description)}</small></header>
    """
    )


def cards(items):
    palette = [
        ("#d79b17", "#fff4d5"),
        ("#15947d", "#e3f6ee"),
        ("#4b83bf", "#e8f2fc"),
        ("#9570b2", "#f4edf9"),
    ]
    blocks = []
    for index, (label, value, note) in enumerate(items):
        accent, wash = palette[index % len(palette)]
        blocks.append(
            f'<article class="hf-card" style="--accent:{accent};--wash:{wash}">'
            f"{escape(label)}<strong>{escape(value)}</strong><small>{escape(note)}</small></article>"
        )
    st.html('<div class="hf-grid">' + "".join(blocks) + "</div>")


def series(df, unit, mode="Line"):
    graph = px.bar if mode == "Bars" else px.line
    fig = graph(df, color_discrete_sequence=COLORS)
    fig.update_layout(
        yaxis_title=unit,
        xaxis_title=None,
        legend_title=None,
        legend_orientation="h",
        hovermode="x unified",
        margin=dict(l=8, r=8, t=8, b=8),
        barmode="group",
    )
    st.plotly_chart(fig, width="stretch")


def csv_button(label, df, name):
    st.download_button(label, df.to_csv(index=False), name, "text/csv")
