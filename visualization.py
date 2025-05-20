# visualization.py
# Visualization functions for rendering maps

import streamlit as st
import pydeck as pdk
import pandas as pd


def draw_colored_device_map(df, scale_factor, strings):
    if df.empty:
        st.warning(strings["map_warning"])
        return

    status_color_map = {
        "OK": [0, 180, 0],
        "WARN": [255, 165, 0],
        "ERROR": [255, 0, 0]
    }

    df["color"] = df["status"].map(lambda x: status_color_map.get(x, [120, 120, 120]))
    df["radius"] = df["battery"].apply(
        lambda b: 60 * scale_factor if pd.isna(b) else (50 + (min(max(b, 0), 100) / 100.0) * 250) * scale_factor)

    view_state = pdk.ViewState(
        longitude=df["longitude"].mean(),
        latitude=df["latitude"].mean(),
        zoom=6
    )

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[longitude, latitude]',
        get_radius="radius",
        get_fill_color="color",
        pickable=True
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            map_style="mapbox://styles/mapbox/light-v9",
            tooltip={
                "html": "<b>{}</b>: {{device_id}}<br><b>{}</b>: {{status}}<br><b>{}</b>: {{battery}}%".format(
                    strings["device_id"], strings["status"], strings["battery"]
                ),
                "style": {"backgroundColor": "steelblue", "color": "white"}
            }
        ),
        height=650
    )


def draw_basic_device_map(df, scale_factor, strings):
    if df.empty:
        st.warning(strings["map_warning"])
        return

    df["color"] = [[0, 120, 255] for _ in range(len(df))]
    df["radius"] = 50 * scale_factor

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[longitude, latitude]',
        get_radius="radius",
        get_fill_color="color",
        pickable=True
    )

    view_state = pdk.ViewState(
        longitude=df["longitude"].mean(),
        latitude=df["latitude"].mean(),
        zoom=6,
        pitch=0
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            map_style="mapbox://styles/mapbox/light-v9",
            tooltip={"text": "{}: {{device_id}}".format(strings["device_id"])}
        ),
        height=650
    )
