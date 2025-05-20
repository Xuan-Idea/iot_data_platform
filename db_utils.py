# db_utils.py
# Database utility functions

import psycopg2
import pandas as pd
import json
import time
import streamlit as st
from config import DB_CONFIG, LANGUAGES


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def truncate_device_data_table(strings):
    try:
        conn = get_connection()
        st.write(f"数据库连接: {conn.info.dbname}")  # 调试日志
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("TRUNCATE TABLE public.device_data;")  # 明确指定 public 模式
        cur.execute("SELECT COUNT(*) FROM public.device_data;")
        count = cur.fetchone()[0]
        st.write(f"清空后记录数: {count}")  # 验证清空结果
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(strings["truncate_error"].format(error=e))
        print(f"清空错误: {e}")  # 控制台日志
        return False


def init_spatial_extension(strings):
    try:
        conn = get_connection()
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        cur.execute("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name='device_data' AND column_name='geom'
                ) THEN
                    ALTER TABLE device_data ADD COLUMN geom geometry(Point, 4326);
                END IF;
            END $$;
        """)
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(strings["init_spatial_error"].format(error=e))
        return False


def update_geometry(strings):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE device_data
            SET geom = ST_SetSRID(
                ST_MakePoint(
                    (location->>'lon')::FLOAT,
                    (location->>'lat')::FLOAT
                ),
                4326
            )
            WHERE location IS NOT NULL
            AND (location->>'lon') IS NOT NULL
            AND (location->>'lat') IS NOT NULL;
        """)
        conn.commit()
        affected_rows = cur.rowcount
        cur.close()
        conn.close()
        return affected_rows
    except Exception as e:
        st.error(strings["update_geometry_error"].format(error=e))
        return 0


def bulk_insert_records(records, strings, with_notes=False):
    try:
        conn = get_connection()
        cur = conn.cursor()

        insert_sql = """
            INSERT INTO device_data (device_id, timestamp, location, data, notes)
            VALUES (%s, %s, %s, %s, %s)
        """ if with_notes else """
            INSERT INTO device_data (device_id, timestamp, location, data)
            VALUES (%s, %s, %s, %s)
        """

        BATCH_SIZE = 500
        batch = []
        success_count = 0
        skip_count = 0
        start_time = time.time()

        for i, record in enumerate(records):
            try:
                device_id = record.get("device_id")
                timestamp = record.get("timestamp")
                location = json.dumps(record.get("location", {}), ensure_ascii=False)
                data = json.dumps(record.get("data", {}), ensure_ascii=False)
                notes = record.get("notes") if with_notes else None

                if not device_id or not timestamp:
                    skip_count += 1
                    continue

                if with_notes:
                    batch.append((device_id, timestamp, location, data, notes))
                else:
                    batch.append((device_id, timestamp, location, data))

                if len(batch) >= BATCH_SIZE:
                    cur.executemany(insert_sql, batch)
                    conn.commit()
                    success_count += len(batch)
                    batch.clear()

            except Exception as e:
                skip_count += 1
                continue

        if batch:
            cur.executemany(insert_sql, batch)
            conn.commit()
            success_count += len(batch)

        end_time = time.time()
        elapsed = end_time - start_time

        cur.close()
        conn.close()

        return success_count, skip_count, elapsed
    except Exception as e:
        st.error(strings["insert_error"])
        return 0, 0, 0


def query_data(min_temp, max_temp, min_battery, status_list, region_filter, strings, limit=None, offset=0,
               all_records=False):
    conn = get_connection()
    cur = conn.cursor()

    sql = """
        SELECT device_id,
               timestamp,
               (data->>'temperature')::FLOAT AS temperature,
               (data->>'battery')::FLOAT AS battery,
               (data->>'status') AS status,
               (location->>'region') AS region
        FROM device_data
    """
    params = []
    conditions = []

    if not all_records:
        conditions.append("(data->>'temperature')::FLOAT BETWEEN %s AND %s")
        conditions.append("(data->>'battery')::FLOAT >= %s")
        conditions.append("(data->>'status') = ANY(%s)")
        conditions.append("(location->>'region') LIKE %s")
        params = [min_temp, max_temp, min_battery, status_list, f"%{region_filter}%"]

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY timestamp DESC"

    if limit is not None and not all_records:
        sql += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])

    start_time = time.time()
    cur.execute(sql, params)
    rows = cur.fetchall()
    elapsed_time = time.time() - start_time

    columns = ["device_id", "timestamp", "temperature", "battery", "status", "region"]
    df = pd.DataFrame(rows, columns=columns)
    cur.close()
    conn.close()
    return df, elapsed_time


def query_nearby_devices_with_attributes(lon, lat, radius_km=5):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT 
            device_id,
            ST_X(geom) AS longitude,
            ST_Y(geom) AS latitude,
            (data->>'battery')::FLOAT AS battery,
            (data->>'status') AS status,
            (ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(%s, %s),4326)::geography) / 1000.0) AS distance_km
        FROM device_data
        WHERE ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_MakePoint(%s, %s),4326)::geography,
            %s * 1000
        )
        ORDER BY distance_km;
    """
    cur.execute(query, (lon, lat, lon, lat, radius_km))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return pd.DataFrame(rows, columns=["device_id", "longitude", "latitude", "battery", "status", "distance_km"])


def query_all_devices(limit=1000000):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT device_id,
               ST_X(geom) AS longitude,
               ST_Y(geom) AS latitude
        FROM device_data
        WHERE geom IS NOT NULL
        LIMIT %s;
    """
    cur.execute(query, (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return pd.DataFrame(rows, columns=["device_id", "longitude", "latitude"])
