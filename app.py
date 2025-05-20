# app.py
# Main Streamlit application for IoT Data Platform

import streamlit as st
import json
import random
import pandas as pd
from datetime import datetime
import os
from data_generator import generate_records  # 导入自定义模块：生成模拟 IoT 数据的函数
from config import LANGUAGES  # 语言配置文件：用于多语言切换
from db_utils import (  # 包括清表、插入、查询等数据库操作封装
    truncate_device_data_table,
    init_spatial_extension,
    update_geometry,
    bulk_insert_records,
    query_data,
    query_nearby_devices_with_attributes,
    query_all_devices
)
from visualization import (  # 地图可视化函数（基于 pydeck）
    draw_colored_device_map,
    draw_basic_device_map
)

# --- Main Streamlit App ---
st.set_page_config(page_title="IoT Data Platform", layout="wide")  # 设置页面标题和布局宽度

# Language selection
if "language" not in st.session_state:
    st.session_state.language = "en"  # 初始化语言状态（默认英文）

strings = LANGUAGES[st.session_state.language]  # 加载对应语言的字符串字典（从 config.py）

# Title and language selector（顶部标题和语言切换下拉框）
col1, col2 = st.columns([4, 1])  # 顶部分成两栏，左边放标题，右边放语言切换
with col1:
    st.title(strings["title"])
with col2:
    language_code = st.selectbox(
        label=strings["language_label"],
        options=["en", "zh"],
        format_func=lambda code: "English" if code == "en" else "中文",
        index=0 if st.session_state.language == "en" else 1
    )
    st.session_state.language = language_code
    strings = LANGUAGES[st.session_state.language]

# Sidebar（侧边栏）
with st.sidebar:
    st.header(strings["sidebar_header"])

    # Clear Device Data Table with Confirmation Button
    # 清空数据库表按钮（含二次确认）
    if "show_truncate_confirm" not in st.session_state:
        st.session_state.show_truncate_confirm = False

    if st.button(strings["truncate_button"], key="truncate_table"):
        st.session_state.show_truncate_confirm = True

    if st.session_state.show_truncate_confirm:
        st.warning(strings["truncate_confirm"])
        col1, col2 = st.columns(2)
        with col1:
            if st.button(strings["confirm_clear_button"], key="confirm_clear"):
                with st.spinner("Clearing device_data table..."):
                    if truncate_device_data_table(strings):
                        st.success(strings["truncate_success"])
                        # Clear last query cache to ensure fresh data
                        if 'last_query_df' in st.session_state:
                            del st.session_state['last_query_df']
                    st.session_state.show_truncate_confirm = False
        with col2:
            if st.button(strings["cancel_clear_button"], key="cancel_clear"):
                st.session_state.show_truncate_confirm = False
                # st.experimental_rerun()  # 强制刷新 UI

    # 数据生成配置输入项（用于 tab1）
    filename_base = st.text_input(strings["filename_label"], st.session_state.get("filename_base",
                                                                                  f"iot_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"))
    st.session_state.filename_base = filename_base
    record_count = st.number_input(strings["record_count_label"], 1000, 1000000, 15000, step=1000)  # 生成记录数量
    directory_path = st.text_input(strings["storage_path_label"], "./Simulation/data")  # 存储路径
    save_format = st.selectbox(strings["save_format_label"], ["JSON", "CSV"])  # 保存格式（JSON 或 CSV）
    preview_count = st.slider(strings["preview_count_label"], 1, 100, 10)  # 预览条数
    force_gps = st.checkbox(strings["force_gps_label"], False)  # 是否强制生成 GPS/加速度信息
    force_accelerometer = st.checkbox(strings["force_accelerometer_label"], False)
    battery_miss_rate = st.slider(strings["battery_miss_rate_label"], 0.0, 0.5, 0.05, step=0.01)  # 缺失值比例（电量、气压）
    pressure_miss_rate = st.slider(strings["pressure_miss_rate_label"], 0.0, 0.5, 0.05, step=0.01)
    with_notes = st.checkbox(strings["with_notes_label"], False)  # 是否添加备注

# Initialize session state
if "generated_records" not in st.session_state:
    st.session_state.generated_records = []

# --- Tabs ---
tab1, tab2, tab3 = st.tabs([strings["tab1_title"], strings["tab2_title"], strings["tab3_title"]])

# --- Tab 1: Generate, Save & Insert ---
with tab1:
    st.subheader(strings["generate_sub"])

    with st.expander(strings["generate_subheader"], expanded=True):
        if st.button(strings["generate_button"], key="generate"):
            with st.spinner(strings["generating"]):
                try:
                    st.session_state.generated_records = []
                    progress_bar = st.progress(0)
                    batch_size = 1000  # 分批生成记录（最多1000条）便于进度条刷新

                    for i in range(0, record_count, batch_size):
                        count = min(batch_size, record_count - i)
                        batch = generate_records(count)
                        for rec in batch:
                            if random.random() < battery_miss_rate:
                                rec["data"]["battery"] = None
                            if random.random() < pressure_miss_rate:
                                rec["data"]["pressure"] = None
                            if force_gps:
                                rec["data"]["gps"] = {
                                    "satellites": random.randint(5, 20),
                                    "hdop": round(random.uniform(0.5, 3.0), 2)
                                }
                            if force_accelerometer:
                                rec["data"]["acceleration"] = {
                                    "x": round(random.uniform(-10, 10), 2),
                                    "y": round(random.uniform(-10, 10), 2),
                                    "z": round(random.uniform(-10, 10), 2)
                                }
                            if with_notes:
                                rec["notes"] = f"Generated at {datetime.now().isoformat()}"
                        st.session_state.generated_records.extend(batch)
                        progress_bar.progress(min((i + count) / record_count, 1.0))

                    st.success(strings["generate_success"].format(count=len(st.session_state.generated_records)))

                    if not os.path.exists(directory_path):
                        os.makedirs(directory_path)
                    file_path = os.path.join(directory_path, f"{st.session_state.filename_base}.{save_format.lower()}")

                    if save_format == "JSON":
                        with open(file_path, "w", encoding="utf-8") as f:
                            json.dump(st.session_state.generated_records, f, ensure_ascii=False, indent=2)
                    else:
                        flat_records = []
                        for rec in st.session_state.generated_records:
                            flat = {
                                "device_id": rec["device_id"],
                                "timestamp": rec["timestamp"],
                                "region": rec["location"]["region"],
                                "lat": rec["location"]["lat"],
                                "lon": rec["location"]["lon"],
                                "altitude": rec["location"]["altitude"],
                                "temperature": rec["data"]["temperature"],
                                "humidity": rec["data"]["humidity"],
                                "battery": rec["data"].get("battery"),
                                "pressure": rec["data"].get("pressure"),
                                "status": rec["data"]["status"],
                                "noise_db": rec["data"]["metrics"]["noise"]["db"],
                                "low_freq": rec["data"]["metrics"]["noise"]["spectrum"]["low_freq"],
                                "mid_freq": rec["data"]["metrics"]["noise"]["spectrum"]["mid_freq"],
                                "high_freq": rec["data"]["metrics"]["noise"]["spectrum"]["high_freq"],
                                "vib_x": rec["data"]["metrics"]["vibration"]["x"],
                                "vib_y": rec["data"]["metrics"]["vibration"]["y"],
                                "vib_z": rec["data"]["metrics"]["vibration"]["z"],
                                "image_path": rec["data"]["image_path"],
                            }
                            gps = rec["data"].get("gps")
                            if gps:
                                flat["satellites"] = gps["satellites"]
                                flat["hdop"] = gps["hdop"]
                            acc = rec["data"].get("acceleration")
                            if acc:
                                flat["acc_x"] = acc["x"]
                                flat["acc_y"] = acc["y"]
                                flat["acc_z"] = acc["z"]
                            if with_notes:
                                flat["notes"] = rec.get("notes")
                            flat_records.append(flat)
                        pd.DataFrame(flat_records).to_csv(file_path, index=False, encoding="utf-8-sig")

                    st.success(strings["save_success"].format(path=file_path))
                except ImportError as e:
                    st.error(
                        "❌ Failed to import data_generator: {error}. Please ensure the file is in the correct "
                        "directory.".format(error=e))
                except Exception as e:
                    st.error("❌ Data generation failed: {error}".format(error=e))

        if st.session_state.generated_records:
            st.subheader(strings["data_preview"])
            st.json(st.session_state.generated_records[:preview_count])

    with st.expander(strings["insert_spatial_subheader"]):
        col1, col2 = st.columns([3, 1])
        # 将模拟数据插入数据库
        with col1:
            if st.session_state.generated_records:
                st.info(strings["insert_info"].format(count=len(st.session_state.generated_records)))
                if st.button(strings["insert_button"], key="insert"):
                    with st.spinner(strings["inserting"]):
                        success_count, skip_count, elapsed = bulk_insert_records(st.session_state.generated_records,
                                                                                 strings, with_notes)
                        if success_count > 0:
                            st.success(strings["insert_success"].format(success=success_count, skip=skip_count,
                                                                        elapsed=elapsed))
                        else:
                            st.error(strings["insert_error"])
            else:
                st.warning(strings["insert_warning"])
        # 初始化空间扩展、更新空间字段（geometry），用于空间查询
        with col2:
            if st.button(strings["init_spatial_button"], key="init_spatial"):
                with st.spinner(strings["init_spatial"]):
                    if init_spatial_extension(strings):
                        st.success(strings["init_spatial_success"])

            if st.button(strings["update_geometry_button"], key="update_geometry"):
                with st.spinner(strings["update_geometry"]):
                    affected_rows = update_geometry(strings)
                    if affected_rows > 0:
                        st.success(strings["update_geometry_success"].format(count=affected_rows))
                    else:
                        st.warning(strings["update_geometry_warning"])

# --- Tab 2: Basic Query ---
with tab2:
    col1, col2 = st.columns([1, 2])
    # 左侧：条件表单输入（温度、电量、状态、区域名），分页输入
    with col1:
        st.subheader(strings["query_subheader"])
        with st.form("query_form"):
            min_temp = st.number_input(strings["min_temp_label"], -10.0, 50.0, 0.0)
            max_temp = st.number_input(strings["max_temp_label"], -10.0, 50.0, 50.0)
            min_battery = st.number_input(strings["min_battery_label"], 0.0, 100.0, 20.0)
            status_options = st.multiselect(strings["status_label"], ["OK", "WARN", "ERROR"],
                                            default=["OK", "WARN", "ERROR"])
            region_filter = st.text_input(strings["region_label"], "")
            page = st.number_input(strings["page_label"], 1, 1000, 1)
            limit = 50
            offset = (page - 1) * limit
            col_query, col_all = st.columns(2)
            with col_query:
                query_submitted = st.form_submit_button(strings["query_button"])
            with col_all:
                all_submitted = st.form_submit_button(strings["query_all_button"])

        if query_submitted:
            with st.spinner(strings["querying"]):
                try:
                    df, query_time = query_data(min_temp, max_temp, min_battery, status_options, region_filter, strings,
                                                limit,
                                                offset)
                    if df.empty:
                        st.warning(strings["query_warning"])
                    else:
                        st.session_state['last_query_df'] = df
                        st.session_state['query_success'] = strings["query_success"].format(count=len(df),
                                                                                            time=query_time)
                except Exception as e:
                    st.error(strings["query_error"].format(error=e))

        if all_submitted:
            with st.spinner(strings["querying_all"]):
                try:
                    df, query_time = query_data(0, 0, 0, [], "", strings, all_records=True)
                    if df.empty:
                        st.warning(strings["query_all_warning"])
                    else:
                        st.session_state['last_query_df'] = df
                        st.session_state['query_success'] = strings["query_success"].format(count=len(df),
                                                                                            time=query_time)
                except Exception as e:
                    st.error(strings["query_error"].format(error=e))
    # 右侧：显示查询结果 DataFrame 并可导出为 CSV
    with col2:
        st.subheader(strings["query_results_subheader"])
        if 'query_success' in st.session_state:
            st.success(st.session_state['query_success'])
        if 'last_query_df' in st.session_state:
            st.dataframe(st.session_state['last_query_df'], use_container_width=True, height=500)
            csv = st.session_state['last_query_df'].to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button(strings["download_csv"], csv, "iot_query_results.csv", "text/csv")
        else:
            st.info(strings["query_info"])

# --- Tab 3: Spatial Query ---
with tab3:
    col1, col2 = st.columns([1, 2])
    # 输入经纬度、半径，查询附近设备
    with col1:
        st.subheader(strings["spatial_subheader"])
        with st.form("spatial_query_form"):
            lon = st.number_input(strings["lon_label"], value=121.4737, format="%.6f")
            lat = st.number_input(strings["lat_label"], value=31.2304, format="%.6f")
            radius = st.slider(strings["radius_label"], 1, 100, 25)
            point_scale = st.slider(strings["point_scale_label"], 0.5, 5.0, 2.5, step=0.1)
            col_nearby, col_all = st.columns(2)
            with col_nearby:
                nearby_submitted = st.form_submit_button(strings["nearby_button"])
            with col_all:
                all_devices_submitted = st.form_submit_button(strings["all_devices_button"])

        if nearby_submitted:
            st.session_state.query_mode = "nearby"
            st.session_state.lon = lon
            st.session_state.lat = lat
            st.session_state.radius = radius
            st.session_state.point_scale = point_scale
            st.session_state.df = query_nearby_devices_with_attributes(lon, lat, radius)

        if all_devices_submitted:
            st.session_state.query_mode = "all"
            st.session_state.point_scale = point_scale
            st.session_state.df = query_all_devices(limit=1000000)

        if "df" in st.session_state:
            st.dataframe(st.session_state.df, height=325)
    # 调用 PyDeck 进行地图可视化展示
    with col2:
        st.subheader(strings["spatial_results_subheader"])
        point_scale = st.session_state.get("point_scale", 1.0)
        if st.session_state.get("query_mode") == "nearby":
            st.subheader(strings["nearby_results"].format(radius=st.session_state.radius))
            with st.spinner(strings["querying_nearby"]):
                # 查询某点附近设备
                df = query_nearby_devices_with_attributes(st.session_state.lon, st.session_state.lat,
                                                          st.session_state.radius)
            if df.empty:
                st.warning(strings["nearby_warning"])
            else:
                st.success(strings["nearby_success"].format(count=len(df)))
                draw_colored_device_map(df, point_scale, strings)

        elif st.session_state.get("query_mode") == "all":
            st.subheader(strings["all_devices_results"])
            with st.spinner(strings["querying_all_devices"]):
                # 查询全部设备
                df = query_all_devices(limit=1000000)
                # 实际验证1M级数据大概是250MB，但Streamlit前端数据限制200MB
                # 通过修改streamlit配置文件.streamlit/config.toml，键入server.maxMessageSize = 300
                # 可能会导致网页加载缓慢，内存占用增大
            if df.empty:
                st.warning(strings["all_devices_warning"])
            else:
                st.success(strings["all_devices_success"].format(count=len(df)))
                draw_basic_device_map(df, point_scale, strings)
