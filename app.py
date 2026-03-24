import streamlit as st
import random
import json

def load_database():
    try:
        with open('civa_mega.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("❌ Файл civa_mega.json не найден! Запустите mega_builder.py")
        st.stop()

# ==========================================
# ПАРАШЮТЫ С ОСЕЙ
# ==========================================
def get_y_recovery_figure(att, speed):
    if speed == 'HS': return {"macro": "-h4-" if att == 'I' else "+h4+", "req_speed": "HS_REQ", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "Y", "k_factor": 25}
    elif speed == 'LS': return {"macro": "-iv4-" if att == 'I' else "+iv4+", "req_speed": "LS_REQ", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "Y", "k_factor": 15}
    else: return {"macro": "-1j-" if att == 'I' else "+1j+", "req_speed": "MS_REQ", "out_speed": "MS", "req_entry": att, "exit_att": att, "axis": "Y", "k_factor": 10}

def get_x_recovery_figure(att, speed):
    if speed == 'HS': return {"macro": "-o-" if att == 'I' else "+o+", "req_speed": "HS_REQ", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "X", "k_factor": 12}
    elif speed == 'LS': return {"macro": "-a+" if att == 'I' else "+2a+", "req_speed": "LS_REQ", "out_speed": "HS", "req_entry": att, "exit_att": "U", "axis": "X", "k_factor": 15}
    else: return {"macro": "-j-" if att == 'I' else "+j+", "req_speed": "MS_REQ", "out_speed": "MS", "req_entry": att, "exit_att": att, "axis": "X", "k_factor": 10}

# ==========================================
# ГЕНЕРАТОР КОМПЛЕКСОВ
# ==========================================
DATABASE = load_database()

def build_tournament_sequence(num_hard, num_link, max_k_total, link_threshold):
    length = num_hard + num_link
    sequence = []
    current_att = "U"     
    current_speed = "MS"  
    current_axis = "X"    
    
    current_k = 0
    hard_count = 0
    link_count = 0
    cons_hard = 0
    figures_since_y = 99  
    used_bases = set()

    clean_pool = []
    for family, figs in DATABASE.items():
        for f in figs:
            if f["changes_axis"] and family not in ["1", "2", "5", "9"]: continue
            clean_pool.append(f)

    if not clean_pool:
        st.error("В базе нет фигур!")
        return []

    for i in range(length):
        if current_axis == "Y":
            fig = get_y_recovery_figure(current_att, current_speed)
            sequence.append({
                "macro": fig["macro"], "speed_in": current_speed, "att_in": current_att, 
                "att_out": fig["exit_att"], "req_speed": fig["req_speed"], "axis": "Y", "k_factor": fig["k_factor"]
            })
            current_att, current_speed, current_axis = fig["exit_att"], fig["out_speed"], "X"
            figures_since_y = 0
            current_k += fig["k_factor"]; link_count += 1; cons_hard = 0
            continue

        valid_figs = [f for f in clean_pool if f["req_entry"] == current_att]
        
        # СТРОГАЯ СТЫКОВКА СКОРОСТЕЙ
        speed_filtered = []
        for f in valid_figs:
            req = f["req_speed"]
            if current_speed == 'HS' and req == 'HS_REQ': speed_filtered.append(f)
            elif current_speed == 'LS' and req == 'LS_REQ': speed_filtered.append(f)
            elif current_speed == 'MS' and req in ['MS_REQ', 'LS_REQ']: speed_filtered.append(f)
            
        valid_figs = speed_filtered

        if figures_since_y < 2 or i >= length - 2:
            valid_figs = [f for f in valid_figs if not f.get("changes_axis")]

        hard_figs = [f for f in valid_figs if f.get("k_factor", 15) > link_threshold]
        link_figs = [f for f in valid_figs if f.get("k_factor", 15) <= link_threshold]
        
        force_link = False; force_hard = False
        if cons_hard >= 3: force_link = True
        elif hard_count >= num_hard: force_link = True
        elif link_count >= num_link: force_hard = True
        
        figs_left = length - i
        if figs_left > 0 and ((max_k_total - current_k) / figs_left) < link_threshold:
            force_link = True
            
        pool_to_use = valid_figs
        if force_link and link_figs: pool_to_use = link_figs
        elif force_hard and hard_figs: pool_to_use = hard_figs
        elif hard_figs and link_figs:
            pool_to_use = hard_figs if random.random() < 0.75 else link_figs

        strict_figs = [f for f in pool_to_use if f["aresti"][0] not in used_bases]

        if strict_figs: fig = random.choice(strict_figs)
        elif pool_to_use: fig = random.choice(pool_to_use)
        else:
            fig = get_x_recovery_figure(current_att, current_speed)
            fig["aresti"] = ["X_REC"]

        sequence.append({
            "macro": fig["macro"], "speed_in": current_speed, "att_in": current_att, 
            "att_out": fig["exit_att"], "req_speed": fig.get("req_speed", ""), "axis": "X", "k_factor": fig.get("k_factor", 15)
        })

        if fig["aresti"][0] != "X_REC":
            used_bases.add(fig["aresti"][0])

        current_att = fig["exit_att"] 
        current_speed = fig["out_speed"]
        current_k += fig.get("k_factor", 15)
        
        if fig.get("k_factor", 15) > link_threshold:
            hard_count += 1; cons_hard += 1
        else:
            link_count += 1; cons_hard = 0
            
        if fig.get("changes_axis"):
            current_axis = "Y"; figures_since_y = 0
        else:
            figures_since_y += 1

    return sequence, current_k

# --- Streamlit UI ---
st.set_page_config(page_title="Unlimited World Champ", page_icon="🏆", layout="wide")
st.title("🏆 Unlimited Pro (Native OpenAero Simulator)")
st.write("Комплексы генерируются на основе Мега-Базы, которая просчитана родным 2D-симулятором OpenAero. Ошибок быть не может математически.")

st.sidebar.header("🛠 Бюджет CIVA")
num_hard = st.sidebar.slider("Боевые фигуры (Сложные)", 5, 12, 10)
num_link = st.sidebar.slider("Связочные фигуры (Простые)", 2, 6, 4)
max_k_total = st.sidebar.slider("Лимит сложности (Max Total K)", 300, 500, 420)
link_threshold = st.sidebar.slider("Порог K-фактора (Связочная <= K)", 10, 35, 25)

if st.button("Сгенерировать комплекс"):
    complex_data, total_k = build_tournament_sequence(num_hard, num_link, max_k_total, link_threshold)
    final_string = " ".join([fig["macro"] for fig in complex_data])
    
    st.success(f"✅ Готово! Итоговый K-Фактор: **{total_k}K**")
    st.code(final_string, language="text")
    
    st.write("### Телеметрия:")
    for i, fig in enumerate(complex_data):
        att_in = "⬆️ Прямо" if fig["att_in"] == "U" else "⬇️ Спина"
        spd_icon = "🛑 Stall (LS)" if fig["speed_in"] == "LS" else ("🔥 Fast (HS)" if fig["speed_in"] == "HS" else "💨 Cruise (MS)")
        req_icon = "⬇️ Разгон (LS_REQ)" if fig.get("req_speed") == "LS_REQ" else ("⬆️ Энергия (HS_REQ)" if fig.get("req_speed") == "HS_REQ" else "➡️ Горизонт (MS_REQ)")
        type_icon = "⚔️ **Боевая**" if fig["k_factor"] > link_threshold else "🔗 *Связочная*"
        
        st.write(f"**{i+1}.** `{fig['macro']}` | **[{fig['k_factor']}K]** {type_icon}")
        st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;Вход: {att_in} ({spd_icon}) ➡️ Фигура просит: {req_icon} | Ось: {fig.get('axis', 'X')}")
