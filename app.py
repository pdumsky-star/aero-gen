import streamlit as st
import random
import json
import re

def load_database():
    try:
        with open('civa_database.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("❌ Файл civa_database.json не найден! Запустите parser.py")
        st.stop()

# ==========================================
# 1. АНАЛИЗАТОР ФИЗИКИ (ИДЕАЛЬНАЯ СИНХРОНИЗАЦИЯ)
# ==========================================
def does_figure_change_axis(aresti_list):
    changes = False
    for code in aresti_list:
        parts = code.split('.')
        if len(parts) == 4:
            family, sub, row, col = map(int, parts)
            # Ряды 1 (90°) и 3 (270°) меняют ось
            if family == 2 and row in [1, 3]: changes = not changes 
            elif family == 9 and col % 2 != 0:
                if sub <= 10 and row in [3, 5]: changes = not changes
                elif sub in [11, 12, 13] and row == 1: changes = not changes
    return changes

def get_attitudes(macro, aresti_list):
    m_clean = re.sub(r'[^a-zA-Z0-9\+\-]', '', macro)
    explicit_in = 'I' if m_clean.startswith('-') else ('U' if m_clean.startswith('+') else None)
    explicit_out = 'I' if m_clean.endswith('-') else ('U' if m_clean.endswith('+') else None)
    
    base = aresti_list[0].split('.')
    family, sub, row, col = map(int, base) if len(base) == 4 else (0, 0, 0, 0)
    
    native_entry = 'U' if col in [1, 3] else 'I'
    
    base_flip = False
    if family == 7 and sub in [1, 2, 3]: base_flip = True
    if family == 8 and sub in [5, 6, 7]: base_flip = True
    if family == 1 and sub == 2 and row in [9, 10, 11, 12]: base_flip = True
    if family == 6: base_flip = True # Колокола и скольжения опрокидывают самолет
    
    roll_flips = sum(1 for c in aresti_list[1:] if len(c.split('.')) == 4 and c.startswith('9') and c.split('.')[3] in ['2', '6'])
    net_flip = base_flip ^ (roll_flips % 2 != 0)
    
    req_entry = explicit_in if explicit_in else native_entry
    exit_att = explicit_out if explicit_out else ('I' if (req_entry == 'U' and net_flip) or (req_entry == 'I' and not net_flip) else 'U')
        
    return req_entry, exit_att

def analyze_figure(f_data):
    aresti_list = f_data["aresti"]
    macro = f_data["macro"]
    base = aresti_list[0]
    parts = base.split('.')
    family, sub, row, col = map(int, parts) if len(parts) == 4 else (0, 0, 0, 0)

    roll_codes = aresti_list[1:]
    has_spin = any(r.split('.')[1] in ['11', '12', '13'] for r in roll_codes if len(r.split('.')) == 4)
    has_flick = any(r.split('.')[1] in ['9', '10'] for r in roll_codes if len(r.split('.')) == 4)

    req_entry, exit_att = get_attitudes(macro, aresti_list)

    starts_dir = 'HORIZ' 
    out_speed = 'MS'     

    if family == 1:
        is_down = any(x in macro.lower() for x in ['iv', 'it', 'k', 'ik'])
        is_up = any(x in macro.lower() for x in ['v', 't', 'p']) and not is_down
        if is_down: starts_dir = 'DOWN'
        elif is_up: starts_dir = 'UP'
    elif family in [5, 6]: starts_dir = 'UP'
    elif family == 7: starts_dir = 'UP' if row in [1, 2, 5] else 'DOWN'
    elif family == 8:
        if sub in [1, 2, 3, 4, 13, 14]: starts_dir = 'UP' if row in [1, 2, 3, 4] else 'DOWN'
        elif sub in [15, 16, 17, 18]: starts_dir = 'UP' if sub in [15, 17] else 'DOWN'
        elif sub in [5, 6]: starts_dir = 'UP' if row in [1, 2, 3, 4] else 'DOWN'
        elif sub == 8: starts_dir = 'UP' if row in [1, 2, 3, 4] else 'DOWN'

    if has_spin: starts_dir = 'SPIN'

    if family == 1:
        if sub == 1: out_speed = 'MS' if row <= 5 else ('LS' if col in [1, 2] else 'HS')
        elif sub in [2, 3, 4]: out_speed = 'HS' if row in [3,4,5,6, 10,11,13,16] else 'LS'
    elif family in [5, 6]: out_speed = 'HS' 
    elif family == 7:
        if sub in [1, 2]: out_speed = 'LS' if row in [1, 2] else 'HS'
        elif sub in [3, 4]: out_speed = 'HS'
    elif family == 8:
        if sub in [1, 2, 3, 4, 13, 14, 5, 6]: out_speed = 'HS' if row in [1, 2, 3, 4] else 'LS'
        elif sub in [15, 16, 17, 18]: out_speed = 'HS' if sub in [15, 18] else 'LS'
        elif sub == 8: out_speed = 'LS' if row in [1, 2, 3, 4] else 'HS'

    return {
        "family": family, "sub": sub, "base_code": base, "roll_codes": roll_codes,
        "starts_dir": starts_dir, "out_speed": out_speed, "req_entry": req_entry, "exit_att": exit_att,
        "is_complex": len(aresti_list) >= 3, "changes_axis": does_figure_change_axis(aresti_list),
        "has_spin": has_spin, "has_flick": has_flick, "k_factor": f_data.get("k_factor", 15)
    }

# ==========================================
# 2. ПАРАШЮТЫ С ОСЕЙ
# ==========================================
def get_y_recovery_figure(att, speed):
    if speed == 'HS': return {"macro": "-h4-" if att == 'I' else "+h4+", "aresti": ["5.2.1.2", "9.1.5.1"] if att == 'I' else ["5.2.1.1", "9.1.5.1"], "starts_dir": "UP", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "Y", "changes_axis": True, "k_factor": 25, "has_flick": False}
    elif speed == 'LS': return {"macro": "-iv4-" if att == 'I' else "+iv4+", "aresti": ["1.1.6.4", "9.1.5.1"] if att == 'I' else ["1.1.6.3", "9.1.5.1"], "starts_dir": "DOWN", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "Y", "changes_axis": True, "k_factor": 15, "has_flick": False}
    else: return {"macro": "-1j-" if att == 'I' else "+1j+", "aresti": ["2.1.1.2"] if att == 'I' else ["2.1.1.1"], "starts_dir": "HORIZ", "out_speed": "MS", "req_entry": att, "exit_att": att, "axis": "Y", "changes_axis": True, "k_factor": 10, "has_flick": False}

def get_x_recovery_figure(att, speed):
    if speed == 'HS': return {"macro": "-o-" if att == 'I' else "+o+", "aresti": ["7.4.2.1"] if att == 'I' else ["7.4.1.1"], "starts_dir": "UP", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "X", "changes_axis": False, "k_factor": 12, "has_flick": False}
    elif speed == 'LS': return {"macro": "-a+" if att == 'I' else "+2a+", "aresti": ["7.2.3.3"] if att == 'I' else ["7.2.3.3", "9.1.3.2"], "starts_dir": "DOWN", "out_speed": "HS", "req_entry": att, "exit_att": "U", "axis": "X", "changes_axis": False, "k_factor": 15, "has_flick": False}
    else: return {"macro": "-j-" if att == 'I' else "+j+", "aresti": ["2.2.1.2"] if att == 'I' else ["2.2.1.1"], "starts_dir": "HORIZ", "out_speed": "MS", "req_entry": att, "exit_att": att, "axis": "X", "changes_axis": False, "k_factor": 10, "has_flick": False}

# ==========================================
# 3. ГЕНЕРАТОР (СТРОГИЕ СКОРОСТИ + МЕНЕДЖЕР K-ФАКТОРА)
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
    used_rolls = set()

    clean_pool = []
    for family, figs in DATABASE.items():
        for f in figs:
            physics = analyze_figure(f)
            if physics["changes_axis"] and physics["family"] not in [1, 2, 5]: continue
            
            fig_copy = f.copy()
            fig_copy.update(physics)
            clean_pool.append(fig_copy)

    if not clean_pool:
        st.error("В базе нет валидных фигур! Проверьте парсер.")
        return []

    for i in range(length):
        if current_axis == "Y":
            fig = get_y_recovery_figure(current_att, current_speed)
            sequence.append({
                "macro": fig["macro"], "speed_in": current_speed, "att_in": current_att, 
                "att_out": fig["exit_att"], "starts_dir": fig["starts_dir"], "axis": "Y", "k_factor": fig["k_factor"]
            })
            current_att, current_speed, current_axis = fig["exit_att"], fig["out_speed"], "X"
            figures_since_y = 0
            current_k += fig["k_factor"]
            link_count += 1
            cons_hard = 0
            continue

        valid_figs = [f for f in clean_pool if f["req_entry"] == current_att]
        
        speed_filtered = []
        for f in valid_figs:
            sd = f["starts_dir"]
            if current_speed == 'HS' and f.get("has_flick"): continue
            # ЗОЛОТОЕ ПРАВИЛО:
            if current_speed == 'LS' and sd in ['DOWN', 'SPIN']: speed_filtered.append(f)
            elif current_speed == 'HS' and sd in ['UP', 'HORIZ']: speed_filtered.append(f)
            elif current_speed == 'MS' and sd in ['DOWN', 'HORIZ']: speed_filtered.append(f)
            
        valid_figs = speed_filtered

        if figures_since_y < 2 or i >= length - 2:
            valid_figs = [f for f in valid_figs if not f.get("changes_axis")]

        hard_figs = [f for f in valid_figs if f.get("k_factor", 15) > link_threshold]
        link_figs = [f for f in valid_figs if f.get("k_factor", 15) <= link_threshold]
        
        force_link = False
        force_hard = False
        
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

        strict_figs = [f for f in pool_to_use if f.get("base_code") not in used_bases and not any(r in f.get("roll_codes", []) for r in used_rolls)]

        if strict_figs: fig = random.choice(strict_figs)
        elif pool_to_use: fig = random.choice(pool_to_use)
        else:
            fig = get_x_recovery_figure(current_att, current_speed)
            fig["base_code"] = "X_REC"
            fig["roll_codes"] = []

        sequence.append({
            "macro": fig["macro"], "speed_in": current_speed, "att_in": current_att, 
            "att_out": fig["exit_att"], "starts_dir": fig.get("starts_dir", ""), "axis": "X", "k_factor": fig.get("k_factor", 15)
        })

        if "base_code" in fig and fig["base_code"] != "X_REC":
            used_bases.add(fig["base_code"])
            used_rolls.update(fig.get("roll_codes", []))

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
st.title("🏆 Unlimited Pro (True Sync Edition)")
st.write("Сборка с идеальной синхронизацией базы и золотыми законами физики (MS -> DOWN/HORIZ).")

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
        dir_icon = "⬇️ Вниз" if fig.get("starts_dir") == "DOWN" else ("⬆️ Вверх" if fig.get("starts_dir") == "UP" else ("➡️ Горизонт" if fig.get("starts_dir") == "HORIZ" else "🌀 Вращение"))
        type_icon = "⚔️ **Боевая**" if fig["k_factor"] > link_threshold else "🔗 *Связочная*"
        
        st.write(f"**{i+1}.** `{fig['macro']}` | **[{fig['k_factor']}K]** {type_icon}")
        st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;Вход: {att_in} ({spd_icon}) ➡️ Вектор: {dir_icon} | Ось: {fig.get('axis', 'X')}")
