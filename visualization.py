# visualization.py
# Visualization functions for rendering device maps using Streamlit and Pydeck

import streamlit as st
import pydeck as pdk
import pandas as pd


def draw_colored_device_map(df, scale_factor, strings):
    """
    绘制带有颜色编码和电量半径缩放的设备地图。

    参数：
        df (DataFrame): 包含设备信息的数据框，需包含 'latitude', 'longitude', 'status', 'battery', 'device_id' 列。
        scale_factor (float): 缩放因子，控制点的显示大小。
        strings (dict): 本地化或自定义显示字符串，如提示信息或标签。
    """
    if df.empty:
        st.warning(strings["map_warning"])  # 数据为空时提示警告信息
        return

    # 状态对应颜色映射：正常为绿色，警告为橙色，错误为红色，未知为灰色
    status_color_map = {
        "OK": [0, 180, 0],
        "WARN": [255, 165, 0],
        "ERROR": [255, 0, 0]
    }

    # 根据状态映射颜色；状态未知则使用默认灰色
    df["color"] = df["status"].map(lambda x: status_color_map.get(x, [120, 120, 120]))

    # 根据电池电量计算点半径；电量越高点越大，最大不超过250；缺失值使用默认值
    df["radius"] = df["battery"].apply(
        lambda b: 60 * scale_factor if pd.isna(b) else (50 + (min(max(b, 0), 100) / 100.0) * 250) * scale_factor
    )

    # 设置地图初始视图（以数据平均经纬度为中心）
    view_state = pdk.ViewState(
        longitude=df["longitude"].mean(),
        latitude=df["latitude"].mean(),
        zoom=6
    )

    # 创建散点层
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[longitude, latitude]',  # 获取点的位置
        get_radius="radius",  # 点的半径
        get_fill_color="color",  # 点的颜色
        pickable=True  # 开启交互悬浮提示
    )

    # 渲染地图
    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            map_style="mapbox://styles/mapbox/light-v9",  # 地图样式
            tooltip={  # 设置悬浮提示内容
                "html": "<b>{}</b>: {{device_id}}<br><b>{}</b>: {{status}}<br><b>{}</b>: {{battery}}%".format(
                    strings["device_id"], strings["status"], strings["battery"]
                ),
                "style": {"backgroundColor": "steelblue", "color": "white"}  # 悬浮提示样式
            }
        ),
        height=650
    )


def draw_basic_device_map(df, scale_factor, strings):
    """
    绘制基础设备地图，所有点为统一颜色和大小。

    参数：
        df (DataFrame): 包含设备信息的数据框，需包含 'latitude', 'longitude', 'device_id' 列。
        scale_factor (float): 缩放因子，控制点的大小。
        strings (dict): 本地化或自定义显示字符串，如提示信息或标签。
    """
    if df.empty:
        st.warning(strings["map_warning"])
        return

    # 所有点设为统一颜色（蓝色）
    df["color"] = [[0, 120, 255] for _ in range(len(df))]

    # 所有点的半径一致
    df["radius"] = 50 * scale_factor

    # 创建散点图层
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[longitude, latitude]',
        get_radius="radius",
        get_fill_color="color",
        pickable=True
    )

    # 设置地图视图
    view_state = pdk.ViewState(
        longitude=df["longitude"].mean(),
        latitude=df["latitude"].mean(),
        zoom=6,
        pitch=0
    )

    # 渲染地图
    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            map_style="mapbox://styles/mapbox/light-v9",
            tooltip={"text": "{}: {{device_id}}".format(strings["device_id"])}  # 显示设备ID
        ),
        height=650
    )
