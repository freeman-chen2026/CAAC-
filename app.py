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
    let waitingForNext = false;

    window.n = function() {{
        if (waitingForNext) {{
            waitingForNext = false;
            console.log('⏩ 继续下一航班...');
        }} else {{
            console.log('⏳ 没有等待中的航班，请先运行脚本。');
        }}
    }};
    window.next = window.n;

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

    // 优化版 findButtonByText，优先通过类名定位
    function findButtonByText(text) {{
        // 1. 精准定位 mini-button-text
        const spans = document.querySelectorAll('span.mini-button-text');
        for (let span of spans) {{
            if (span.innerText.trim() === text) {{
                let btn = span.closest('a') || span.closest('button') || span;
                return btn;
            }}
        }}
        // 2. 通用查找
        const candidates = document.querySelectorAll('a, button, span, div, input[type="button"], input[type="submit"]');
        for (let el of candidates) {{
            let txt = el.innerText || el.textContent || el.value || '';
            if (txt.trim() === text) {{
                let btn = el.closest('a') || el.closest('button') || el;
                return btn;
            }}
        }}
        // 3. XPath 兜底
        const xpath = "//*[normalize-space(text())='" + text + "' or normalize-space(@value)='" + text + "']";
        const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
        if (result.singleNodeValue) {{
            let el = result.singleNodeValue;
            return el.closest('a') || el.closest('button') || el;
        }}
        return null;
    }}

    function setValue(id, value) {{
        if (typeof mini !== 'undefined' && mini.get) {{
            let controlId = id;
            if (id.endsWith('$text')) {{
                controlId = id.slice(0, -5);
            }}
            const control = mini.get(controlId);
            if (control) {{
                control.setValue(value);
                if (control.doValueChanged) control.doValueChanged();
                if (control.fireEvent) control.fireEvent('valuechanged', {{ sender: control, value: value }});
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

        console.log(`✅ 航班 ${{index+1}}/${{flights.length}} 已填充，请检查并点击“保存”。`);
        console.log(`📌 保存完成后，在控制台输入 n() 并回车继续。`);

        // 4. 等待用户输入 n()
        waitingForNext = true;
        await new Promise((resolve) => {{
            const check = setInterval(() => {{
                if (!waitingForNext) {{
                    clearInterval(check);
                    resolve();
                }}
            }}, 200);
        }});

        // 5. 继续下一航班
        processFlight(index + 1);
    }}

    console.log('🚀 脚本已启动。填充后请点击“保存”，然后输入 n() 继续。');
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
            actype_mapping = build_actype_mapping()
            flights = process_excel(df, actype_mapping)

            if not flights:
                st.error("❌ 未提取到任何有效航班数据，请检查 Excel 格式是否正确。")
            else:
                st.success(f"✅ 成功提取 {len(flights)} 个航班记录。")
                
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
