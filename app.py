import streamlit as st
import random
import json
import re

def load_database():
    try:
        with open('civa_database.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("❌ Файл civa_database.json не найден! Закиньте спарсенную базу.")
        st.stop()

# ==========================================
# 1. АБСОЛЮТНАЯ ФИЗИКА ПО КАТАЛОГУ АРЕСТИ
# ==========================================
def analyze_figure(f_data):
    aresti_list = f_data["aresti"]
    macro = f_data["macro"]
    base = aresti_list[0]
    parts = base.split('.')
    family, sub, row, col = map(int, parts) if len(parts) == 4 else (0, 0, 0, 0)

    roll_codes = aresti_list[1:]
    has_spin = any(r.split('.')[1] in ['11', '12', '13', '14'] for r in roll_codes if len(r.split('.')) == 4)
    has_flick = any(r.split('.')[1] in ['9', '10'] for r in roll_codes if len(r.split('.')) == 4)

    # --- 1. ГЕОМЕТРИЯ ПЕРЕВОРОТОВ ---
    base_flip = False
    # Переворачивают только: Полупетли, 3/4 петли, Кубанки, P-петли, Q-петли
    if family == 7 and sub in [1, 2, 3]: base_flip = True
    if family == 8 and sub in [5, 6, 7]: base_flip = True
    
    # Считаем полубочки (колонки 2 и 6 в Family 9)
    roll_flips = sum(1 for c in roll_codes if len(c.split('.')) == 4 and c.split('.')[3] in ['2', '6'])
    net_flip = base_flip ^ (roll_flips % 2 != 0)
    
    # Вытаскиваем жесткие требования судей из макроса (+ или -)
    m_clean = re.sub(r'[^a-zA-Z0-9\+\-]', '', macro)
    req_entry = 'I' if m_clean.startswith('-') else 'U'
    
    # Считаем выход: если судья явно не поставил знак выхода, считаем математически
    if m_clean.endswith('-'): exit_att = 'I'
    elif m_clean.endswith('+'): exit_att = 'U'
    else: exit_att = 'I' if (req_entry == 'U' and net_flip) or (req_entry == 'I' and not net_flip) else 'U'

    # --- 2. ГЕОМЕТРИЯ СКОРОСТЕЙ (СТРОГАЯ) ---
    starts_up = False; starts_down = False
    exits_up = False; exits_down = False

    if family == 1:
        if sub == 1:
            if row == 6: starts_up = True; exits_up = True
            if row == 7: starts_down = True; exits_down = True
        elif sub >= 2:
            if row in [1, 2, 3, 4, 9, 10, 13, 14]: starts_up = True
            else: starts_down = True
            if sub == 2:
                if row in [3, 4, 5, 6, 10, 11, 13, 16]: exits_down = True
                else: exits_up = True
            else:
                if row in [5, 6, 7, 8, 11, 12, 15, 16]: exits_down = True
                else: exits_up = True
    elif family in [5, 6]:
        starts_up = True; exits_down = True
    elif family == 7:
        if sub == 2: # Полупетли
            if row in [1, 2]: starts_up = True; exits_up = True
            if row in [3, 4]: starts_down = True; exits_down = True
        elif sub == 3: # 3/4 петли
            if row in [1, 2, 5]: starts_up = True
            if row in [3, 4, 6]: starts_down = True
            if row in [2, 4]: exits_up = True
            if row in [1, 3]: exits_down = True
        elif sub == 4: # Целые петли
            if row in [1, 4, 5]: starts_up = True
            if row in [2, 3, 6]: starts_down = True
        elif sub == 8: # Горизонтальные восьмерки
            if col in [1, 2]: starts_up = True
            if col in [3, 4]: starts_down = True
    elif family == 8:
        # Все Кубанки и Хумпти стартуют так: колонки 1,2 - вверх, 3,4 - вниз
        if col in [1, 2]: starts_up = True
        if col in [3, 4]: starts_down = True
        if sub in [4, 5, 6, 7]: # Хумпти, Кубанки, P, Q
            if col in [1, 2]: exits_down = True
            if col in [3, 4]: exits_up = True
        elif sub == 8: # Двойные Хумпти
            if col in [1, 2]: exits_up = True
            if col in [3, 4]: exits_down = True

    if starts_up: req_speed = 'HS_REQ'
    elif starts_down: req_speed = 'LS_REQ'
    else: req_speed = 'MS_REQ'

    if exits_up: out_speed = 'LS'
    elif exits_down: out_speed = 'HS'
    else: out_speed = 'MS'

    if has_spin: req_speed = 'LS_REQ'

    # --- 3. ГЕОМЕТРИЯ ОСИ Y ---
    changes_axis = False
    # Виражи (Сем 2): 90° (ряд 1) и 270° (ряд 3)
    if family == 2 and row in [1, 3]: changes_axis = True
    
    # Бочки: 1/4 и 3/4 (колонки 3,4,5,7) меняют ось только на вертикалях
    roll_changes = sum(1 for c in roll_codes if len(c.split('.')) == 4 and c.split('.')[3] in ['3', '4', '5', '7'])
    if roll_changes % 2 != 0:
        if (family == 1 and sub == 1 and row in [6, 7]) or (family in [7, 8] and starts_up and exits_down):
            changes_axis = not changes_axis

    return {
        "family": family, "base_code": base, "roll_codes": roll_codes,
        "req_speed": req_speed, "out_speed": out_speed, 
        "req_entry": req_entry, "exit_att": exit_att, 
        "changes_axis": changes_axis, "has_flick": has_flick, 
        "k_factor": f_data.get("k_factor", 15)
    }

# ==========================================
# 2. ПАРАШЮТЫ С ОСЕЙ (СВЯЗКИ)
# ==========================================
def get_y_recovery_figure(att, speed):
    if speed == 'HS': return {"macro": "-h4-" if att == 'I' else "+h4+", "req_speed": "HS_REQ", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "Y", "changes_axis": True, "k_factor": 25}
    elif speed == 'LS': return {"macro": "-iv4-" if att == 'I' else "+iv4+", "req_speed": "LS_REQ", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "Y", "changes_axis": True, "k_factor": 15}
    else: return {"macro": "-1j-" if att == 'I' else "+1j+", "req_speed": "MS_REQ", "out_speed": "MS", "req_entry": att, "exit_att": att, "axis": "Y", "changes_axis": True, "k_factor": 10}

def get_x_recovery_figure(att, speed):
    if speed == 'HS': return {"macro": "-o-" if att == 'I' else "+o+", "req_speed": "HS_REQ", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "X", "changes_axis": False, "k_factor": 12}
    elif speed == 'LS': return {"macro": "-a+" if att == 'I' else "+2a+", "req_speed": "LS_REQ", "out_speed": "HS", "req_entry": att, "exit_att": "U", "axis": "X", "changes_axis": False, "k_factor": 15}
    else: return {"macro": "-j-" if att == 'I' else "+j+", "req_speed": "MS_REQ", "out_speed": "MS", "req_entry": att, "exit_att": att, "axis": "X", "changes_axis": False, "k_factor": 10}

# ==========================================
# 3. ГЕНЕРАТОР КОМПЛЕКСОВ
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
            physics = analyze_figure(f)
            if physics["changes_axis"] and physics["family"] not in [1, 2, 5, 8, 9]: continue
            
            fig_copy = f.copy()
            fig_copy.update(physics)
            clean_pool.append(fig_copy)

    if not clean_pool:
        st.error("В базе нет валидных фигур!")
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

        valid_figs = []
        for f in clean_pool:
            if f["req_entry"] != current_att: continue
            if current_speed == 'HS' and f.get("has_flick"): continue
            
            # СТРОГАЯ СТЫКОВКА СКОРОСТЕЙ
            req = f["req_speed"]
            match_speed = False
            if current_speed == 'HS' and req == 'HS_REQ': match_speed = True
            elif current_speed == 'LS' and req == 'LS_REQ': match_speed = True
            elif current_speed == 'MS' and req in ['MS_REQ', 'LS_REQ']: match_speed = True
            
            if match_speed: valid_figs.append(f)

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

        strict_figs = [f for f in pool_to_use if f["base_code"] not in used_bases]

        if strict_figs: fig = random.choice(strict_figs)
        elif pool_to_use: fig = random.choice(pool_to_use)
        else:
            fig = get_x_recovery_figure(current_att, current_speed)
            fig["base_code"] = "X_REC"

        # МАКРОС ИДЕТ В OPENAERO В ОРИГИНАЛЬНОМ ВИДЕ!
        sequence.append({
            "macro": fig["macro"], "speed_in": current_speed, "att_in": current_att, 
            "att_out": fig["exit_att"], "req_speed": fig.get("req_speed", ""), "axis": "X", "k_factor": fig.get("k_factor", 15)
        })

        if fig["base_code"] != "X_REC":
            used_bases.add(fig["base_code"])

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
st.title("🏆 Unlimited Pro (The Absolute Aresti Math)")
st.write("Использует спарсенную базу реальных комплексов. Физика вычисляется математически по каталогу Арести.")

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
