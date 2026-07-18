import streamlit as st
import pandas as pd
import json

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

def process_excel(df, actype_mapping):
    flights = []
    df.columns = df.columns.str.strip()
    
    st.write("📌 **读取到的列名：**", df.columns.tolist())
    st.write("📌 **数据预览（前3行）：**")
    st.dataframe(df.head(3))
    
    required_cols = ['航班号', '飞机注册号', '用途', '出发日期', '计划出发', '预计到达', '出发地', '到达地']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        st.error(f"❌ 缺少以下必需列：{missing}。请检查 Excel 表头是否正确。")
        return flights
    
    for idx, row in df.iterrows():
        if pd.isna(row.get('航班号')):
            continue
        
        purpose = str(row.get('用途', '')).strip()
        nature = '调机飞行' if ('调机' in purpose or '维修' in purpose) else '公务飞行'
        
        reg = str(row.get('飞机注册号', '')).strip()
        actype = actype_mapping.get(reg, '')
        if not actype:
            st.warning(f"未找到注册号 '{reg}' 对应的机型，请手动补充映射表。")
        
        date_val = row.get('出发日期')
        if pd.notna(date_val):
            if isinstance(date_val, pd.Timestamp):
                date_str = date_val.strftime('%Y-%m-%d')
            else:
                date_str = str(date_val).strip()
        else:
            date_str = ''
        
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

def generate_js_script(flights):
    flights_json = json.dumps(flights, ensure_ascii=False, indent=2)
    script = f"""
(function() {{
    const flights = {flights_json};

    // 通用等待元素（通过 ID）
    function waitForElement(id, timeout) {{
        return new Promise((resolve, reject) => {{
            const start = Date.now();
            const interval = setInterval(() => {{
                const el = document.getElementById(id);
                if (el) {{
                    clearInterval(interval);
                    resolve(el);
                }} else if (Date.now() - start > timeout) {{
                    clearInterval(interval);
                    reject(new Error('等待元素超时: ' + id));
                }}
            }}, 200);
        }});
    }}

    // 查找包含指定文本的按钮（不区分大小写）
    function findButtonByText(text) {{
        const candidates = document.querySelectorAll('a, button, span, div, input[type="button"], input[type="submit"]');
        for (let el of candidates) {{
            let txt = el.innerText || el.textContent || el.value || '';
            if (txt.trim() === text) {{
                let btn = el.closest('a') || el.closest('button') || el;
                return btn;
            }}
        }}
        // XPath 兜底
        const xpath = "//*[normalize-space(text())='" + text + "' or normalize-space(@value)='" + text + "']";
        const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
        if (result.singleNodeValue) {{
            let el = result.singleNodeValue;
            return el.closest('a') || el.closest('button') || el;
        }}
        return null;
    }}

    // 增强版 setValue，优先使用 MiniUI
    function setValue(id, value) {{
        if (typeof mini !== 'undefined' && mini.get) {{
            const control = mini.get(id);
            if (control) {{
                control.setValue(value);
                if (control.doValueChanged) control.doValueChanged();
                return;
            }}
        }}
        const el = document.getElementById(id);
        if (el) {{
            el.value = value;
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            el.dispatchEvent(new Event('blur', {{ bubbles: true }}));
        }}
    }}

    // 等待保存完成（检测“新增”按钮再次变为可用，或弹窗消失）
    async function waitForSaveComplete() {{
        // 等待“新增”按钮重新出现且可点击（最多等待20秒）
        for (let attempt = 0; attempt < 40; attempt++) {{
            const addBtn = findButtonByText('新增');
            if (addBtn && !addBtn.disabled && addBtn.style.display !== 'none') {{
                // 额外检查是否有遮罩（有些系统保存后会遮罩）
                const mask = document.querySelector('.mini-mask, .ui-widget-overlay, .modal-backdrop');
                if (!mask || mask.style.display === 'none') {{
                    return true;
                }}
            }}
            await new Promise(r => setTimeout(r, 500));
        }}
        return false;
    }}

    async function processFlight(index) {{
        if (index >= flights.length) {{
            console.log('✅ 所有航班录入完成！');
            return;
        }}
        const flight = flights[index];

        // 1. 点击“新增”
        let addBtn = null;
        for (let attempt = 0; attempt < 5; attempt++) {{
            addBtn = findButtonByText('新增');
            if (addBtn) break;
            await new Promise(r => setTimeout(r, 300));
        }}
        if (!addBtn) {{
            console.error('❌ 找不到“新增”按钮，停止执行。');
            return;
        }}
        addBtn.click();

        // 2. 等待表单加载
        try {{
            await waitForElement('FLIGHTID_ADD$text', 5000);
        }} catch (e) {{
            console.error('❌ 新增表单未加载', e);
            return;
        }}

        // 3. 填充字段
        setValue('MPROPERTY_ADD$text', flight.nature);
        setValue('FLIGHTID_ADD$text', flight.reg);
        setValue('REGNUM_ADD$text', flight.reg);
        setValue('ACTYPE_ADD$text', flight.actype);
        setValue('EDATE_ADD$text', flight.date);
        const dateHidden = document.getElementById('EDATE_ADD$value');
        if (dateHidden) dateHidden.value = flight.date;
        setValue('DEPAP_ADD$text', flight.depap);
        setValue('DEPTIME_ADD$text', flight.deptime);
        setValue('ARRTIME_ADD$text', flight.arrtime);
        setValue('ARRAP_ADD$text', flight.arrap);

        console.log(`✅ 航班 ${index+1}/${flights.length} 已填充完毕。请人工检查并点击“保存”按钮。`);

        // 4. 等待用户手动点击“保存”，并检测保存完成
        const saveCompleted = await waitForSaveComplete();
        if (!saveCompleted) {{
            console.warn('⚠️ 未检测到保存完成，可能“新增”按钮未恢复。但会尝试继续下一个航班。');
        }} else {{
            console.log(`✅ 航班 ${index+1} 保存完成。`);
        }}

        // 5. 继续下一个航班
        processFlight(index + 1);
    }}

    console.log('🚀 脚本已启动。填充后请人工检查并点击“保存”，脚本会自动识别并继续。');
    processFlight(0);
}})();
"""
    return script

def main():
    st.set_page_config(page_title="飞行计划录入脚本生成器", layout="wide")
    st.title("✈️ 飞行计划录入脚本生成器")
    st.markdown("上传 Excel 航段数据，自动生成 Edge 浏览器控制台可执行的 JavaScript 批量录入脚本。")

    uploaded_file = st.file_uploader("选择 Excel 文件（.xlsx）", type=["xlsx"])

    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file, sheet_name=0, header=1)
            st.subheader("📋 数据预览（前 10 行）")
            st.dataframe(df.head(10))

            actype_mapping = build_actype_mapping()
            flights = process_excel(df, actype_mapping)

            if not flights:
                st.error("❌ 未提取到任何有效航班数据，请根据上方列名提示检查 Excel 格式。")
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
