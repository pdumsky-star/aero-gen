import streamlit as st
import random
import json
import re

def load_database():
    try:
        with open('civa_database.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("❌ Файл civa_database.json не найден!")
        st.stop()

# ==========================================
# 1. АНАЛИЗАТОР ФИЗИКИ (ОРИГИНАЛ ОТ 1 МАРТА)
# ==========================================
def does_figure_change_axis(aresti_list):
    changes = False
    for code in aresti_list:
        parts = code.split('.')
        if len(parts) == 4:
            family = int(parts[0])
            sub = int(parts[1])
            row = int(parts[2])
            col = int(parts[3])
            
            if family == 2 and sub in [1, 3]: changes = not changes 
            elif family == 9 and col % 2 != 0:
                if sub <= 10 and row in [3, 5]: changes = not changes
                elif sub in [11, 12, 13] and row == 1: changes = not changes
    return changes

def analyze_figure(f_data):
    aresti_list = f_data["aresti"]
    macro = f_data["macro"].lower()
    base = aresti_list[0]
    parts = base.split('.')
    family = int(parts[0])
    sub = int(parts[1]) if len(parts) > 1 else 0
    row = int(parts[2]) if len(parts) > 2 else 0
    col = int(parts[3]) if len(parts) > 3 else 0

    roll_codes = aresti_list[1:]
    has_spin = any(r.split('.')[1] in ['11', '12', '13'] for r in roll_codes if len(r.split('.')) == 4)
    has_flick = any(r.split('.')[1] in ['9', '10'] for r in roll_codes if len(r.split('.')) == 4)

    # 1. ЧТЕНИЕ ПОЛОЖЕНИЯ ПО МАКРОСУ (+/-)
    m_clean = re.sub(r'[^a-z0-9\+\-]', '', macro)
    req_entry = 'I' if m_clean.startswith('-') else 'U'
    exit_att = 'I' if m_clean.endswith('-') else 'U'

    # 2. МАТРИЦА ВЕКТОРОВ И СКОРОСТЕЙ (ТОТ САМЫЙ РАБОЧИЙ АЛГОРИТМ)
    starts_up = False; starts_down = False
    exits_up = False; exits_down = False

    if family == 1:
        is_down = any(x in m_clean for x in ['iv', 'it', 'k', 'ik'])
        is_up = any(x in m_clean for x in ['v', 't', 'p']) and not is_down
        if is_down: starts_down = True; exits_down = True
        elif is_up: starts_up = True; exits_up = True
            
    elif family in [5, 6]: 
        starts_up = True; exits_down = True
        
    elif family == 7: 
        if sub in [1, 2]:
            if row in [1, 2]: starts_up = True; exits_up = True
            if row in [3, 4]: starts_down = True; exits_down = True
        elif sub in [3, 4]:
            if row in [1, 2, 5]: starts_up = True; exits_down = True
            if row in [3, 4, 6]: starts_down = True; exits_up = True
            
    elif family == 8:
        if sub in [1, 2, 3, 4, 13, 14]: 
            if row in [1, 2, 3, 4]: starts_up = True; exits_down = True
            if row in [5, 6, 7, 8]: starts_down = True; exits_up = True
        elif sub in [15, 16, 17, 18]: 
            if sub in [15, 17]: starts_up = True
            if sub in [16, 18]: starts_down = True
            if sub in [15, 18]: exits_down = True
            if sub in [16, 17]: exits_up = True
        elif sub in [5, 6]: 
            if row in [1, 2, 3, 4]: starts_up = True; exits_down = True
            if row in [5, 6, 7, 8]: starts_down = True; exits_up = True
        elif sub == 8: 
            if row in [1, 2, 3, 4]: starts_up = True; exits_up = True
            if row in [5, 6, 7, 8]: starts_down = True; exits_down = True

    # 3. ФИЗИКА ЭНЕРГИИ 
    if starts_up: req_speed = 'HS_REQ'
    elif starts_down: req_speed = 'LS_REQ'
    else: req_speed = 'MS_REQ'

    if exits_up: out_speed = 'LS'
    elif exits_down: out_speed = 'HS'
    else: out_speed = 'MS'

    if has_spin: req_speed = 'LS_REQ'
    elif has_flick and req_speed == 'HS_REQ': req_speed = 'MS_REQ' 

    changes_axis = does_figure_change_axis(aresti_list)
    is_complex = len(aresti_list) >= 3

    return {
        "family": family, "sub": sub, "base_code": base, "roll_codes": roll_codes,
        "out_speed": out_speed, "req_speed": req_speed,
        "req_entry": req_entry, "exit_att": exit_att,
        "is_complex": is_complex, "changes_axis": changes_axis, "has_spin": has_spin, "has_flick": has_flick,
        "k_factor": f_data.get("k_factor", 15)
    }

def is_clean_macro(macro, aresti_list):
    m = macro.lower()
    if any(w in m for w in ["sequence", "generated", "unknown", "training", "unlimited", "free", "known"]): return False
    if not aresti_list or len(aresti_list[0].split('.')) < 4: return False
    m_let = re.sub(r'[^a-z]', '', m)
    if not m_let: return False 
    if aresti_list[0].startswith("1.1.1.") and len(aresti_list) < 2: return False
    return True

# ==========================================
# 2. ПАРАШЮТЫ С ИДЕАЛЬНЫМ OLAN СИНТАКСИСОМ
# ==========================================
def get_y_recovery_figure(att, speed):
    if speed == 'HS': return {"macro": "-h4-" if att == 'I' else "+h4+", "aresti": ["5.2.1.2", "9.1.5.1"] if att == 'I' else ["5.2.1.1", "9.1.5.1"], "req_speed": "HS_REQ", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "Y", "changes_axis": True, "is_complex": False, "has_spin": False, "has_flick": False, "base_code": "5.2.1.1", "roll_codes": ["9.1.5.1"], "family": 5, "sub": 2, "k_factor": 25}
    elif speed == 'LS': return {"macro": "-iv4-" if att == 'I' else "+iv4+", "aresti": ["1.1.6.4", "9.1.5.1"] if att == 'I' else ["1.1.6.3", "9.1.5.1"], "req_speed": "LS_REQ", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "Y", "changes_axis": True, "is_complex": False, "has_spin": False, "has_flick": False, "base_code": "1.1.6.3", "roll_codes": ["9.1.5.1"], "family": 1, "sub": 1, "k_factor": 15}
    else: return {"macro": "-1j-" if att == 'I' else "+1j+", "aresti": ["2.1.1.2"] if att == 'I' else ["2.1.1.1"], "req_speed": "MS_REQ", "out_speed": "MS", "req_entry": att, "exit_att": att, "axis": "Y", "changes_axis": True, "is_complex": False, "has_spin": False, "has_flick": False, "base_code": "2.1.1.1", "roll_codes": [], "family": 2, "sub": 1, "k_factor": 10}

def get_x_recovery_figure(att, speed):
    if speed == 'HS': return {"macro": "-o-" if att == 'I' else "+o+", "aresti": ["7.4.2.1"] if att == 'I' else ["7.4.1.1"], "req_speed": "HS_REQ", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "X", "changes_axis": False, "is_complex": False, "has_spin": False, "has_flick": False, "base_code": "7.4.1.1", "roll_codes": [], "family": 7, "sub": 4, "k_factor": 12}
    elif speed == 'LS': return {"macro": "-a+" if att == 'I' else "+2a+", "aresti": ["7.2.3.3"] if att == 'I' else ["7.2.3.3", "9.1.3.2"], "req_speed": "LS_REQ", "out_speed": "HS", "req_entry": att, "exit_att": "U", "axis": "X", "changes_axis": False, "is_complex": False, "has_spin": False, "has_flick": False, "base_code": "7.2.3.3", "roll_codes": [], "family": 7, "sub": 2, "k_factor": 15}
    else: return {"macro": "-j-" if att == 'I' else "+j+", "aresti": ["2.2.1.2"] if att == 'I' else ["2.2.1.1"], "req_speed": "MS_REQ", "out_speed": "MS", "req_entry": att, "exit_att": att, "axis": "X", "changes_axis": False, "is_complex": False, "has_spin": False, "has_flick": False, "base_code": "2.2.1.1", "roll_codes": [], "family": 2, "sub": 2, "k_factor": 10}

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
    used_rolls = set()

    clean_pool = []
    for family, figs in DATABASE.items():
        for f in figs:
            if is_clean_macro(f["macro"], f["aresti"]):
                physics = analyze_figure(f)
                # Безопасное копирование, чтобы не повредить базу
                fig_entry = f.copy()
                fig_entry.update(physics)
                clean_pool.append(fig_entry)

    if not clean_pool:
        st.error("В базе не осталось валидных фигур!")
        return []

    for i in range(length):
        # 1. АППАРАТНЫЙ ВОЗВРАТ С ОСИ Y
        if current_axis == "Y":
            fig = get_y_recovery_figure(current_att, current_speed)
            sequence.append({
                "macro": fig["macro"],
                "aresti": ", ".join(fig["aresti"]),
                "speed_in": current_speed,
                "att_in": current_att,
                "att_out": fig["exit_att"],
                "req_speed": fig["req_speed"],
                "axis": "Y",
                "k_factor": fig["k_factor"]
            })
            current_att = fig["exit_att"]
            current_speed = fig["out_speed"]
            current_axis = "X"
            figures_since_y = 0
            current_k += fig["k_factor"]
            link_count += 1
            cons_hard = 0
            continue

        # 2. ПОИСК ФИГУРЫ НА ОСИ X
        valid_figs = [f for f in clean_pool if f["req_entry"] == current_att]
        
        # ТОТ САМЫЙ РАБОЧИЙ ФИЛЬТР СКОРОСТЕЙ ИЗ 1 МАРТА
        speed_filtered = []
        for f in valid_figs:
            req = f["req_speed"]
            if current_speed == 'HS' and req == 'HS_REQ': speed_filtered.append(f)
            elif current_speed == 'LS' and req == 'LS_REQ': speed_filtered.append(f)
            elif current_speed == 'MS' and req in ['MS_REQ', 'LS_REQ']: speed_filtered.append(f)
            
        valid_figs = speed_filtered

        # Анти-зигзаг
        if figures_since_y < 2 or i >= length - 2:
            valid_figs = [f for f in valid_figs if not f["changes_axis"]]

        # Менеджер K-Фактора
        hard_figs = [f for f in valid_figs if f["k_factor"] > link_threshold]
        link_figs = [f for f in valid_figs if f["k_factor"] <= link_threshold]
        
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

        strict_figs = [f for f in pool_to_use if f["base_code"] not in used_bases and not any(r in f["roll_codes"] for r in used_rolls)]

        if strict_figs: fig = random.choice(strict_figs)
        elif pool_to_use: fig = random.choice(pool_to_use)
        else:
            fig = get_x_recovery_figure(current_att, current_speed)
            fig["base_code"] = "X_REC"
            fig["roll_codes"] = []

        sequence.append({
            "macro": fig["macro"],
            "aresti": ", ".join(fig["aresti"]) if isinstance(fig["aresti"], list) else fig["aresti"],
            "speed_in": current_speed, "att_in": current_att, "att_out": fig["exit_att"],
            "req_speed": fig.get("req_speed", ""), "axis": "X", "k_factor": fig.get("k_factor", 15)
        })

        if "base_code" in fig and fig["base_code"] != "X_REC":
            used_bases.add(fig["base_code"])
            used_rolls.update(fig["roll_codes"])

        current_att = fig["exit_att"] 
        current_speed = fig["out_speed"]
        current_k += fig.get("k_factor", 15)
        
        if fig.get("k_factor", 15) > link_threshold:
            hard_count += 1
            cons_hard += 1
        else:
            link_count += 1
            cons_hard = 0
            
        if fig.get("changes_axis"):
            current_axis = "Y"
            figures_since_y = 0
        else:
            figures_since_y += 1

    return sequence, current_k

# --- Streamlit UI ---
st.set_page_config(page_title="Unlimited World Champ", page_icon="🏆", layout="wide")
st.title("🏆 Unlimited Pro (The March 1st Base)")
st.write("Идеальный код от 1 марта восстановлен! Скрипт принимает все фигуры, ничего не переделывает и строго соблюдает физику: из крейсера (MS) можно только вниз или в горизонт.")

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
