import plotly.express as px
import streamlit as st

COLORS = ["#08795e", "#407997", "#c47b22", "#536353"]


def header(section, title, description):
    st.caption(section.upper())
    st.title(title)
    st.write(description)


def cards(items):
    for start in range(0, len(items), 4):
        batch = items[start : start + 4]
        for col, (name, value, note) in zip(st.columns(len(batch)), batch):
            with col.container(border=True):
                st.caption(name)
                st.markdown(f"**{value}**")
                st.caption(note)


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
