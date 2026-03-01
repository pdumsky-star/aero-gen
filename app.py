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
# 1. АНАЛИЗАТОР ФИЗИКИ (СОВЕРШЕННАЯ МАТРИЦА)
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
            
            # Виражи (1=90°, 3=270°)
            if family == 2 and sub in [1, 3]: 
                changes = not changes 
            
            # Вращения (Идеальный сканер вертикалей)
            elif family == 9:
                if col % 2 != 0: # Нечетные (1/4, 3/4, 1.25)
                    # Обычные бочки и штопорные на вертикалях (ряды 3 и 5)
                    if sub <= 10 and row in [3, 5]: 
                        changes = not changes
                    # Штопоры (всегда на вертикали вниз - ряд 1)
                    elif sub in [11, 12, 13] and row == 1: 
                        changes = not changes
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

    # 1. ГИБРИДНЫЙ ПАРСЕР ПОЛОЖЕНИЯ (Устранение "autocorrect roll")
    m_clean = re.sub(r'[^a-z0-9\+\-]', '', macro)
    
    explicit_entry = 'I' if m_clean.startswith('-') else ('U' if m_clean.startswith('+') else None)
    explicit_exit = 'I' if m_clean.endswith('-') else ('U' if m_clean.endswith('+') else None)

    native_entry = 'U' if col in [1, 3] else 'I'

    base_flip = False
    if family == 7 and sub in [1, 2]: base_flip = True
    if family == 8 and sub in [5, 7, 8]: base_flip = True 
    if family == 1 and sub == 2 and row in [9, 10, 11, 12]: base_flip = True 

    roll_flips = 0
    for code in roll_codes:
        rp = code.split('.')
        if len(rp) == 4 and rp[0] == '9' and rp[3] in ['2', '6']: roll_flips += 1

    net_flip = base_flip ^ (roll_flips % 2 != 0)
    native_exit = 'I' if (native_entry == 'U' and net_flip) or (native_entry == 'I' and not net_flip) else 'U'

    req_entry = explicit_entry if explicit_entry else native_entry
    exit_att = explicit_exit if explicit_exit else native_exit

    # 2. МАТРИЦА ВЕКТОРОВ И СКОРОСТЕЙ
    starts_dir = 'HORIZ' 
    out_speed = 'MS'     

    if family == 1:
        if sub == 1:
            if row in [6, 7]: starts_dir = 'UP' if col in [1, 2] else 'DOWN'
            elif row in [2, 3, 4, 5]: starts_dir = 'UP' if col in [1, 2] else 'DOWN'
        elif sub in [2, 3, 4]:
            if row in [1,2,3,4, 9,10,13,14]: starts_dir = 'UP'
            elif row in [5,6,7,8, 11,12,15,16]: starts_dir = 'DOWN'
    elif family in [5, 6]: 
        starts_dir = 'UP'
    elif family == 7: 
        if row in [1, 2, 5]: starts_dir = 'UP'
        if row in [3, 4, 6]: starts_dir = 'DOWN'
    elif family == 8:
        if sub in [1, 2, 3, 4, 13, 14, 5, 6, 8]: 
            starts_dir = 'UP' if row in [1, 2, 3, 4] else 'DOWN'
        elif sub in [15, 16, 17, 18]: 
            starts_dir = 'UP' if sub in [15, 17] else 'DOWN'

    if has_spin: starts_dir = 'SPIN'

    if family == 1:
        if sub == 1 and row in [2,3,4,5,6,7]: out_speed = 'LS' if col in [1,2] else 'HS'
        elif sub == 2:
            if row in [3,4,5,6, 10,11,13,16]: out_speed = 'HS'
            elif row in [1,2,7,8, 9,12,14,15]: out_speed = 'LS'
    elif family in [5, 6]: out_speed = 'HS' 
    elif family == 7:
        if sub in [1, 2]: out_speed = 'LS' if row in [1, 2] else 'HS'
        elif sub in [3, 4]: out_speed = 'HS'
    elif family == 8:
        if sub in [1, 2, 3, 4, 13, 14, 5, 6]: out_speed = 'HS' if row in [1, 2, 3, 4] else 'LS'
        elif sub in [15, 16, 17, 18]: out_speed = 'HS' if sub in [15, 18] else 'LS'
        elif sub == 8: out_speed = 'LS' if row in [1, 2, 3, 4] else 'HS'

    changes_axis = does_figure_change_axis(aresti_list)
    is_complex = len(aresti_list) >= 3

    return {
        "family": family, "sub": sub, "base_code": base, "roll_codes": roll_codes,
        "starts_dir": starts_dir, "out_speed": out_speed,
        "req_entry": req_entry, "exit_att": exit_att,
        "is_complex": is_complex, "changes_axis": changes_axis, "has_spin": has_spin, "has_flick": has_flick
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
    if speed == 'HS': return {"macro": "-h4-" if att == 'I' else "+h4+", "aresti": ["5.2.1.2", "9.1.5.1"] if att == 'I' else ["5.2.1.1", "9.1.5.1"], "starts_dir": "UP", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "Y", "changes_axis": True, "is_complex": False, "has_spin": False, "has_flick": False, "base_code": "5.2.1.1"}
    elif speed == 'LS': return {"macro": "-iv4-" if att == 'I' else "+iv4+", "aresti": ["1.1.6.4", "9.1.5.1"] if att == 'I' else ["1.1.6.3", "9.1.5.1"], "starts_dir": "DOWN", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "Y", "changes_axis": True, "is_complex": False, "has_spin": False, "has_flick": False, "base_code": "1.1.6.3"}
    else: return {"macro": "-1j-" if att == 'I' else "+1j+", "aresti": ["2.1.1.2"] if att == 'I' else ["2.1.1.1"], "starts_dir": "HORIZ", "out_speed": "MS", "req_entry": att, "exit_att": att, "axis": "Y", "changes_axis": True, "is_complex": False, "has_spin": False, "has_flick": False, "base_code": "2.1.1.1"}

def get_x_recovery_figure(att, speed):
    if speed == 'HS': return {"macro": "-o-" if att == 'I' else "+o+", "aresti": ["7.4.2.1"] if att == 'I' else ["7.4.1.1"], "starts_dir": "UP", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "X", "changes_axis": False, "is_complex": False, "has_spin": False, "has_flick": False, "base_code": "7.4.1.1"}
    elif speed == 'LS': return {"macro": "-a+" if att == 'I' else "+2a+", "aresti": ["7.2.3.3"] if att == 'I' else ["7.2.3.3", "9.1.3.2"], "starts_dir": "DOWN", "out_speed": "HS", "req_entry": att, "exit_att": "U", "axis": "X", "changes_axis": False, "is_complex": False, "has_spin": False, "has_flick": False, "base_code": "7.2.3.3"}
    else: return {"macro": "-j-" if att == 'I' else "+j+", "aresti": ["2.2.1.2"] if att == 'I' else ["2.2.1.1"], "starts_dir": "HORIZ", "out_speed": "MS", "req_entry": att, "exit_att": att, "axis": "X", "changes_axis": False, "is_complex": False, "has_spin": False, "has_flick": False, "base_code": "2.2.1.1"}

# ==========================================
# 3. ГЕНЕРАТОР КОМПЛЕКСОВ
# ==========================================
DATABASE = load_database()

def build_tournament_sequence(length):
    sequence = []
    current_att = "U"     
    current_speed = "MS"  
    current_axis = "X"    
    cons_complex = 0   
    figures_since_y = 99  
    
    used_bases = set()
    used_rolls = set()

    clean_pool = []
    for family, figs in DATABASE.items():
        for f in figs:
            if is_clean_macro(f["macro"], f["aresti"]):
                physics = analyze_figure(f)
                if physics["changes_axis"] and physics["family"] not in [1, 2, 5]: continue
                f.update(physics)
                clean_pool.append(f)

    if not clean_pool:
        st.error("В базе не осталось валидных фигур!")
        return []

    for i in range(length):
        if current_axis == "Y":
            fig = get_y_recovery_figure(current_att, current_speed)
            sequence.append(fig)
            current_att, current_speed, cons_complex = fig["exit_att"], fig["out_speed"], 0
            current_axis = "X"
            figures_since_y = 0
            continue

        valid_figs = [f for f in clean_pool if f["req_entry"] == current_att]
        
        # --- ИСПРАВЛЕННЫЙ ЖЕСТКИЙ КОНТРОЛЬ СКОРОСТИ ---
        speed_filtered = []
        for f in valid_figs:
            sd = f["starts_dir"]
            
            if current_speed == 'HS' and f["has_flick"]: continue
            
            if current_speed == 'LS' and sd in ['DOWN', 'SPIN']: speed_filtered.append(f)
            elif current_speed == 'HS' and sd in ['UP', 'HORIZ']: speed_filtered.append(f)
            # ГЛАВНОЕ ИСПРАВЛЕНИЕ: Из MS (крейсер) можно только нырять вниз (за скоростью) или делать плоские фигуры!
            elif current_speed == 'MS' and sd in ['DOWN', 'HORIZ']: speed_filtered.append(f)
            
        valid_figs = speed_filtered

        if figures_since_y < 2 or i >= length - 2:
            valid_figs = [f for f in valid_figs if not f["changes_axis"]]

        if not valid_figs:
            fig = get_x_recovery_figure(current_att, current_speed)
            sequence.append(fig)
            current_att, current_speed, cons_complex = fig["exit_att"], fig["out_speed"], 0
            figures_since_y += 1
            continue

        strict_figs = [f for f in valid_figs if not (cons_complex >= 2 and f["is_complex"]) and f["base_code"] not in used_bases and not any(r in used_rolls for r in f["roll_codes"])]

        if strict_figs: fig = random.choice(strict_figs)
        else:
            f1 = [f for f in valid_figs if f["base_code"] not in used_bases and not any(r in used_rolls for r in f["roll_codes"])]
            if f1: fig = random.choice(f1)
            else:
                f2 = [f for f in valid_figs if f["base_code"] not in used_bases]
                if f2: fig = random.choice(f2)
                else: fig = random.choice(valid_figs)

        sequence.append(fig)

        if "base_code" in fig:
            used_bases.add(fig["base_code"])
            used_rolls.update(fig["roll_codes"])

        current_att = fig["exit_att"] 
        current_speed = fig["out_speed"]
        cons_complex = cons_complex + 1 if fig["is_complex"] else 0
        
        if fig["changes_axis"]:
            current_axis = "Y"
            figures_since_y = 0
        else:
            figures_since_y += 1

    return sequence

# --- Streamlit UI ---
st.set_page_config(page_title="Unlimited World Champ", page_icon="🏆")
st.title("🏆 Unlimited Pro (Perfect Physics & Axis)")
st.write("Возвращен Гибридный Парсер для устранения автокоррекций OpenAero. Идеальный трекинг 3/4 штопорных бочек и строгий запрет ухода из крейсера (MS) в вертикаль (UP).")

num_figs = st.sidebar.slider("Количество фигур", 5, 15, 10)

if st.button("Сгенерировать комплекс"):
    complex_data = build_tournament_sequence(num_figs)
    final_string = " ".join([fig["macro"] for fig in complex_data])
    
    st.success("✅ Готово! Копируй в OpenAero и нажимай **Separate figures**.")
    st.code(final_string, language="text")
    
    st.write("### Телеметрия:")
    for i, fig in enumerate(complex_data):
        att_in = "⬆️ Прямо" if fig["att_in"] == "U" else "⬇️ Спина"
        att_out = "⬆️ Прямо" if fig["att_out"] == "U" else "⬇️ Спина"
        spd_icon = "🛑 Stall (LS)" if fig["speed_in"] == "LS" else ("🔥 Energy (HS)" if fig["speed_in"] == "HS" else "💨 Cruiser (MS)")
        
        spin_txt = ""
        if fig.get("has_spin"): spin_txt = "🌀 **ШТОПОР**"
        elif fig.get("has_flick"): spin_txt = "⚡ **ШТОПОРНАЯ БОЧКА**"
        
        dir_icon = "⬇️ Вниз" if fig.get("starts_dir") == "DOWN" else ("⬆️ Вверх" if fig.get("starts_dir") == "UP" else ("➡️ Горизонт" if fig.get("starts_dir") == "HORIZ" else "🌀 Вращение"))
        
        st.write(f"**{i+1}.** `{fig['macro']}` {spin_txt}")
        st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;*Вход:* {att_in} ({spd_icon}) ➡️ *Вектор:* {dir_icon} ➡️ *Выход:* {att_out} | *Ось:* {fig.get('axis', 'X')}")
