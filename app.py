import streamlit as st
import pandas as pd
import json

# ---------- 1. 构建飞机注册号 → 机型映射 ----------
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

# ---------- 3. 生成 JavaScript 自动化脚本（增强版 findAddButton） ----------
def generate_js_script(flights):
    flights_json = json.dumps(flights, ensure_ascii=False, indent=2)
    script = f"""
(function() {{
    const flights = {flights_json};

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

    // 增强版查找“新增”按钮
    function findAddButton() {{
        // 策略1：通过常见的类名和文本
        const candidates = document.querySelectorAll('a.mini-button, span.mini-button-text, .mini-button');
        for (let el of candidates) {{
            let text = el.innerText || el.textContent || '';
            if (text.trim() === '新增') {{
                // 如果是 span，返回其父级 a 标签，确保能点击
                let btn = el.closest('a');
                if (btn) return btn;
                // 如果没有 a，尝试查找可点击的父级
                let parent = el.closest('[onclick]') || el.closest('[role="button"]') || el;
                return parent;
            }}
        }}

        // 策略2：通过 XPath 直接匹配包含“新增”的链接
        const xpath = "//a[.//span[text()='新增'] or .//span[contains(text(),'新增')]] | //*[@class='mini-button-text' and text()='新增']";
        const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
        if (result.singleNodeValue) {{
            let btn = result.singleNodeValue;
            // 如果找到的是 span，尝试取父级 a
            if (btn.tagName.toLowerCase() === 'span') {{
                let a = btn.closest('a');
                if (a) return a;
            }}
            return btn;
        }}

        // 策略3：查找所有包含“新增”文字的任意元素，并取最近的 a 或可点击元素
        const allEls = document.querySelectorAll('*');
        for (let el of allEls) {{
            if (el.innerText && el.innerText.trim() === '新增' && el.tagName !== 'BODY') {{
                let a = el.closest('a');
                if (a) return a;
                // 如果没有 a，但本身可点击
                if (el.onclick || el.getAttribute('role') === 'button') return el;
            }}
        }}

        return null;
    }}

    async function processFlight(index) {{
        if (index >= flights.length) {{
            console.log('✅ 所有航班录入完成！');
            return;
        }}
        const flight = flights[index];

        // 多次尝试点击“新增”（有些页面需要等待）
        let addBtn = null;
        for (let attempt = 0; attempt < 5; attempt++) {{
            addBtn = findAddButton();
            if (addBtn) break;
            await new Promise(r => setTimeout(r, 300));
        }}
        if (!addBtn) {{
            console.error('❌ 经过多次尝试仍找不到“新增”按钮，请确认页面已加载且无遮罩。');
            console.log('💡 提示：请手动关闭可能存在的弹窗或提示框，然后重新运行脚本。');
            return;
        }}
        addBtn.click();

        try {{
            await waitForElement('FLIGHTID_ADD$text', 5000);
        }} catch (e) {{
            console.error('❌ 新增表单未加载', e);
            return;
        }}

        const setValue = (id, value) => {{
            const el = document.getElementById(id);
            if (el) {{
                el.value = value;
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }};

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

        const userConfirmed = confirm(
            `航班 ${{index+1}}/${{flights.length}} 已填充完成。\\n请点击“保存”按钮，然后点击“确定”继续下一个。`
        );
        if (userConfirmed) {{
            processFlight(index + 1);
        }} else {{
            console.log('⏹️ 用户终止录入。');
        }}
    }}

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
