import streamlit as st
import pandas as pd
import json
from io import BytesIO

# ---------- 1. 构建飞机注册号 → 机型 映射 ----------
def build_actype_mapping():
    mapping_text = """GL5T T73338/N2QE
GLEX T7CJK/MLLIN/B8105/N7777U
GL7T N328LM/T7178HT
LJ60 B3926
GLF4 B652Q/B652R/B652S/B65AP/B8262
GLF5 N88AY/B8160/N550DR/B8309/B8292
GLF6 VPCVA/B658L/N777ZH
GA6C VPCEN
F900 N577QT"""
    mapping = {}
    for line in mapping_text.strip().split('\n'):
        parts = line.split()
        if len(parts) < 2:
            continue
        actype = parts[0]
        regs_str = parts[1]
        regs = regs_str.split('/')
        for reg in regs:
            mapping[reg.strip()] = actype
    return mapping

# ---------- 2. 解析 Excel 数据 ----------
def process_excel(df, actype_mapping):
    flights = []
    # 去除列名两端空格，便于匹配
    df.columns = df.columns.str.strip()
    for idx, row in df.iterrows():
        # 跳过空行或缺少关键数据的行
        if pd.isna(row.get('航班号')) or pd.isna(row.get('飞机注册号')):
            continue

        # ---- 飞行性质 ----
        purpose = str(row.get('用途', '')).strip()
        nature = '调机飞行' if ('调机' in purpose or '维修' in purpose) else '公务飞行'

        # ---- 飞机注册号 ----
        reg = str(row.get('飞机注册号', '')).strip()

        # ---- 机型（通过映射） ----
        actype = actype_mapping.get(reg, '')
        if not actype:
            st.warning(f"未找到注册号 '{reg}' 对应的机型，请手动补充映射表或检查注册号是否准确。")

        # ---- 出发日期 ----
        date_val = row.get('出发日期')
        if pd.notna(date_val):
            if isinstance(date_val, pd.Timestamp):
                date_str = date_val.strftime('%Y-%m-%d')
            else:
                date_str = str(date_val).strip()
                try:
                    pd.to_datetime(date_str)  # 验证是否为有效日期
                except:
                    pass  # 保持原样
        else:
            date_str = ''

        # ---- 计划出发时间 (HH:MM → HHMM) ----
        dep_time_val = row.get('计划出发')
        if pd.notna(dep_time_val):
            t = str(dep_time_val).strip()
            if ':' in t:
                h, m = t.split(':')
                deptime = f"{h.zfill(2)}{m.zfill(2)}"
            else:
                deptime = t.replace(':', '')
        else:
            deptime = ''

        # ---- 预计到达时间 (HH:MM → HHMM) ----
        arr_time_val = row.get('预计到达')
        if pd.notna(arr_time_val):
            t = str(arr_time_val).strip()
            if ':' in t:
                h, m = t.split(':')
                arrtime = f"{h.zfill(2)}{m.zfill(2)}"
            else:
                arrtime = t.replace(':', '')
        else:
            arrtime = ''

        # ---- 起降机场（四字码） ----
        depap = str(row.get('出发地', '')).strip() if pd.notna(row.get('出发地')) else ''
        arrap = str(row.get('到达地', '')).strip() if pd.notna(row.get('到达地')) else ''

        flight = {
            'nature': nature,
            'reg': reg,
            'actype': actype,
            'date': date_str,
            'deptime': deptime,
            'arrtime': arrtime,
            'depap': depap,
            'arrap': arrap
        }
        flights.append(flight)
    return flights

# ---------- 3. 生成 JavaScript 自动化脚本 ----------
def generate_js_script(flights):
    # 将航班数据转为 JSON 数组（用于 JS）
    flights_json = json.dumps(flights, ensure_ascii=False, indent=2)

    script = f"""
(function() {{
    // ---------- 从 Excel 提取的航班数据 ----------
    const flights = {flights_json};

    // ---------- 工具：等待元素出现 ----------
    function waitForElement(selector, timeout) {{
        return new Promise((resolve, reject) => {{
            const start = Date.now();
            const interval = setInterval(() => {{
                const el = document.querySelector(selector);
                if (el) {{
                    clearInterval(interval);
                    resolve(el);
                }} else if (Date.now() - start > timeout) {{
                    clearInterval(interval);
                    reject(new Error('等待元素超时: ' + selector));
                }}
            }}, 200);
        }});
    }}

    // ---------- 查找“新增”按钮 ----------
    function findAddButton() {{
        const selectors = [
            'a.mini-button .mini-button-text',
            'span.mini-button-text',
            'a[href="javascript:void(0)"] .mini-button-text'
        ];
        for (let sel of selectors) {{
            const btns = document.querySelectorAll(sel);
            for (let btn of btns) {{
                if (btn.innerText.trim() === '新增') {{
                    return btn.closest('a') || btn;
                }}
            }}
        }}
        return null;
    }}

    // ---------- 处理单个航班 ----------
    async function processFlight(index) {{
        if (index >= flights.length) {{
            console.log('✅ 所有航班录入完成！');
            return;
        }}
        const flight = flights[index];

        // 1. 点击新增
        const addBtn = findAddButton();
        if (!addBtn) {{
            console.error('❌ 找不到“新增”按钮，请确认页面已加载。');
            return;
        }}
        addBtn.click();

        // 2. 等待新增表单出现（以注册号输入框为标志）
        try {{
            await waitForElement('#FLIGHTID_ADD$text', 5000);
        }} catch (e) {{
            console.error('❌ 新增表单未加载', e);
            return;
        }}

        // 3. 填充字段（触发 input 事件以便框架感知）
        const setValue = (id, value) => {{
            const el = document.getElementById(id);
            if (el) {{
                el.value = value;
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }};

        setValue('MPROPERTY_ADD$text', flight.nature);      // 飞行性质
        setValue('FLIGHTID_ADD$text', flight.reg);          // 航班号（注册号）
        setValue('REGNUM_ADD$text', flight.reg);            // 注册号
        setValue('ACTYPE_ADD$text', flight.actype);         // 机型
        setValue('EDATE_ADD$text', flight.date);            // 出发日期
        // 同步隐藏域
        const dateHidden = document.getElementById('EDATE_ADD$value');
        if (dateHidden) dateHidden.value = flight.date;
        setValue('DEPAP_ADD$text', flight.depap);           // 出发地
        setValue('DEPTIME_ADD$text', flight.deptime);       // 计划出发时间
        setValue('ARRTIME_ADD$text', flight.arrtime);       // 预计到达时间
        setValue('ARRAP_ADD$text', flight.arrap);           // 到达地

        // 4. 等待用户手动点击“保存”，然后继续
        const userConfirmed = confirm(
            `航班 ${index+1}/${flights.length} 已填充完成。\\n请点击“保存”按钮，然后点击“确定”继续下一个。`
        );
        if (userConfirmed) {{
            processFlight(index + 1);
        }} else {{
            console.log('⏹️ 用户终止录入。');
        }}
    }}

    // ---------- 启动 ----------
    processFlight(0);
}})();
"""
    return script

# ---------- 4. Streamlit 界面 ----------
def main():
    st.set_page_config(page_title="飞行计划录入脚本生成器", layout="wide")
    st.title("✈️ 飞行计划录入脚本生成器")
    st.markdown("上传 Excel 航段数据，自动生成 Edge 浏览器控制台可执行的 JavaScript 批量录入脚本。")

    uploaded_file = st.file_uploader("选择 Excel 文件（.xlsx）", type=["xlsx"])

    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file, sheet_name=0)
            st.subheader("📋 数据预览（前 10 行）")
            st.dataframe(df.head(10))

            # 构建映射并处理数据
            actype_mapping = build_actype_mapping()
            flights = process_excel(df, actype_mapping)

            if not flights:
                st.error("❌ 未提取到任何有效航班数据，请检查 Excel 格式是否正确（必须包含：航班号、飞机注册号、用途、出发日期、计划出发、预计到达、出发地、到达地）。")
            else:
                st.success(f"✅ 成功提取 {len(flights)} 个航班记录。")
                st.subheader("📌 解析后的航班列表")
                st.dataframe(pd.DataFrame(flights))

                if st.button("🚀 生成 JavaScript 脚本"):
                    script = generate_js_script(flights)
                    st.subheader("📜 生成的脚本（复制到浏览器控制台运行）")
                    st.code(script, language="javascript")

                    st.download_button(
                        label="⬇️ 下载脚本（.js）",
                        data=script,
                        file_name="flight_auto_fill.js",
                        mime="application/javascript"
                    )

        except Exception as e:
            st.error(f"读取文件失败：{e}")

if __name__ == "__main__":
    main()
