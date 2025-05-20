# IoT 数据管理与可视化平台

## 项目概述
`iot_jsonb` 是一个基于 Streamlit 的 Web 应用程序，用于管理、查询和可视化物联网 (IoT) 数据。项目支持生成模拟 IoT 数据、保存为 JSON/CSV 格式、插入 PostgreSQL 数据库（含 PostGIS 空间扩展），并提供基于温度、电量、状态、区域的基础查询和基于地理位置的空间查询。界面支持中英文切换，适合国际化使用。

### 主要功能
1. **数据生成与保存**：
   - 生成包含设备 ID、时间戳、位置（经纬度、区域）、传感器数据（温度、湿度、电量等）的模拟 IoT 数据。
   - 支持保存为 JSON 或 CSV 格式。
2. **数据库操作**：
   - 将生成的数据批量插入 PostgreSQL 数据库。
   - 初始化 PostGIS 空间扩展，更新地理位置字段（`geom`）。
   - 清空设备数据表（`device_data`）。
3. **查询功能**：
   - **基础查询**：根据温度范围、电量、设备状态和区域关键字查询数据，支持分页和 CSV 导出。
   - **空间查询**：基于中心点（经纬度）和半径查询附近设备，或查询所有设备。
4. **数据可视化**：
   - 使用 PyDeck 绘制交互式地图，展示设备位置、状态（OK/WARN/ERROR）和电量。
5. **多语言支持**：
   - 界面支持中文和英文切换，文本配置在 `config.py` 中。

## 项目结构
```
iot_data_platform/
├── app.py                    # 主 Streamlit 应用程序
├── config.py                 # 语言和数据库配置
├── db_utils.py               # 数据库操作工具函数
├── visualization.py          # 地图可视化函数
├── data_generator.py         # 模拟数据生成模块
├── requirements.txt          # 依赖列表
└── README.md                 # 项目说明文档
```

## 环境要求
- **操作系统**：Windows11
- **Python 版本**：3.8 或以上
- **数据库**：PostgreSQL17（需安装 PostGIS 扩展）
- **依赖**：见 `requirements.txt`

## 安装步骤
1. **克隆项目**：
   ```bash
   git clone git@github.com:Xuan-Idea/iot_data_platform.git
   cd iot_data_platform
   ```

2. **安装 Python 依赖**：
   ```bash
   pip install -r requirements.txt
   ```
   依赖包括：
   - `streamlit==1.44.1`
   - `psycopg2-binary==2.0.3`
   - `pandas==2.9.10`
   - `pydeck==0.9.1`

3. **配置 PostgreSQL 数据库**：
   - 安装 PostgreSQL 和 PostGIS：
     ```bash
     # Ubuntu 示例
     sudo apt-get install postgresql postgresql-contrib postgis
     ```
   - 创建数据库：
     ```sql
     psql -U postgres
     CREATE DATABASE iot_data;

     CREATE EXTENSION postgis;
     ```
   - 创建 `device_data` 表（具体见sql）：
     ```sql
     CREATE TABLE public.device_data (
         device_id TEXT,
         timestamp TIMESTAMP,
         location JSONB,
         data JSONB,
         notes TEXT,
         geom geometry(Point, 4326)
     );
     ```
   - 确保 `config.py` 中的 `DB_CONFIG` 正确：
     ```python
     DB_CONFIG = {
         "dbname": "iot_data",
         "user": "postgres",
         "password": "Asd123.456",  # 修改为你的密码
         "host": "localhost",
         "port": "5432",
         "connect_timeout": 5
     }
     ```

4. **运行应用**：
   ```bash
   streamlit run app.py
   ```
   打开浏览器，访问 `http://localhost:8501`。

## 使用说明
1. **界面概览**：
   - **侧边栏**：配置数据生成参数（文件名、记录数、保存路径等），清空数据表，测试数据库连接。
   - **标签页**：
     - **生成、保存与插入**：生成模拟数据，预览，保存为 JSON/CSV，插入数据库。
     - **基础查询**：设置查询条件（温度、电量等），查看结果，下载 CSV。
     - **空间查询**：输入经纬度和半径，查看附近设备地图。

2. **操作示例**：
   - **生成数据**：
     - 在侧边栏设置记录数（例如 15000），选择保存格式（JSON）。
     - 点击“生成数据”，查看预览，确认保存路径。
   - **插入数据库**：
     - 点击“插入生成数据”，等待插入完成。
     - 点击“配置 PostGIS 拓展”和“更新 geom 空间列”以启用空间查询。
   - **清空数据表**：
     - 点击“清除设备数据表”，然后点击“确认清除”执行清空。
     - 点击“取消”关闭确认提示。
   - **查询与可视化**：
     - 在“基础查询”标签页设置条件，点击“查询”或“查询全部”。
     - 在“空间查询”标签页输入经纬度（例如 121.4737, 31.2304）和半径，点击“查询附近”查看地图。

## 故障排查
1. **清空数据表失败**：
   - **现象**：点击“确认清除”后，数据库仍有数据。
   - **解决**：
     - 检查 Streamlit 界面日志（“清空后记录数”）。
     - 验证数据库连接：
       ```bash
       psql -U postgres -d iot_data
       SELECT COUNT(*) FROM public.device_data;
       ```
     - 检查权限：
       ```sql
       SELECT has_table_privilege('postgres', 'public.device_data', 'TRUNCATE');
       GRANT ALL ON public.device_data TO postgres;
       ```
     - 确认表模式：
       ```sql
       \dt public.device_data
       ```
       若表在其他模式，修改 `db_utils.py`：
       ```python
       cur.execute("TRUNCATE TABLE your_schema.device_data;")
       ```

2. **取消按钮未收回提示**：
   - **现象**：点击“取消”后，确认提示和按钮未消失。
   - **解决**：
     - 检查 Streamlit 版本：
       ```bash
       pip show streamlit
       ```
       确保为 1.35.0。若不是，更新：
       ```bash
       pip install streamlit==1.35.0
       ```
     - 清除浏览器缓存或在隐身模式测试。
     - 检查调试日志（“调试: 取消后，show_truncate_confirm = False”）。
     - 重启 Streamlit：
       ```bash
       streamlit run app.py
       ```

3. **数据库连接失败**：
   - **现象**：点击“测试数据库连接”报错。
   - **解决**：
     - 验证 `config.py` 的 `DB_CONFIG`（数据库名、用户、密码等）。
     - 确保 PostgreSQL 运行：
       ```bash
       pg_ctl -D /path/to/postgres/data status
       ```
     - 测试连接：
       ```sql
       psql -U postgres -d iot_data
       ```
