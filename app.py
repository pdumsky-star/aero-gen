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
# 1. АНАЛИЗАТОР ФИЗИКИ И СТРОГАЯ МАТРИЦА АРЕСТИ
# ==========================================
def does_figure_change_axis(aresti_list):
    changes = False
    for code in aresti_list:
        parts = code.split('.')
        if len(parts) == 4:
            family = int(parts[0])
            sub = int(parts[1])
            col = int(parts[3])

            # ИСПРАВЛЕНО: Для виражей (Сем. 2) угол зашит в sub! 1=90°, 3=270°. Они меняют ось.
            if family == 2 and sub in [1, 3]:
                changes = not changes 
            # ИСПРАВЛЕНО: Любое нечетное вращение (1/4, 3/4, 1.25) меняет ось.
            elif family == 9 and col % 2 != 0:
                changes = not changes
    return changes

def analyze_figure(f_data):
    aresti_list = f_data["aresti"]
    macro = f_data["macro"]
    base = aresti_list[0]
    parts = base.split('.')
    family = int(parts[0])
    sub = int(parts[1]) if len(parts) > 1 else 0
    row = int(parts[2]) if len(parts) > 2 else 0
    col = int(parts[3]) if len(parts) > 3 else 0

    roll_codes = aresti_list[1:]
    has_spin = any(r.split('.')[1] in ['11', '12', '13'] for r in roll_codes if len(r.split('.')) == 4)

    # 1. ЖЕСТКОЕ ЧТЕНИЕ ПОЛОЖЕНИЯ ПО ТЕКСТУ (Идеальная склейка)
    m_clean = re.sub(r'[^a-zA-Z0-9\+\-]', '', macro)
    req_entry = 'I' if m_clean.startswith('-') else 'U'
    exit_att = 'I' if m_clean.endswith('-') else 'U'

    # 2. МАТРИЦА ВЕКТОРОВ И СКОРОСТЕЙ
    starts_up = False; starts_down = False
    exits_up = False; exits_down = False

    if family == 1:
        if sub == 1: # Простые линии (ИСПРАВЛЕНО)
            if row in [6, 7]:
                if col in [1, 2]: starts_up = True; exits_up = True
                if col in [3, 4]: starts_down = True; exits_down = True
        elif sub == 2:
            if row in [1,2,3,4, 9,10,13,14]: starts_up = True
            if row in [5,6,7,8, 11,12,15,16]: starts_down = True
            if row in [1,2,7,8, 9,12,14,15]: exits_up = True
            if row in [3,4,5,6, 10,11,13,16]: exits_down = True
        elif sub in [3, 4]:
            if row in [1,2,3,4, 9,10,11,12]: starts_up = True
            if row in [5,6,7,8, 13,14,15,16]: starts_down = True
            exits_down = True
            
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
        elif sub in [15, 16, 17, 18]: # Диагональные Хампти
            if sub in [15, 17]: starts_up = True
            if sub in [16, 18]: starts_down = True
            if sub in [15, 18]: exits_down = True
            if sub in [16, 17]: exits_up = True
        elif sub in [5, 6]: # Кубинцы и P-петли
            if row in [1, 2, 3, 4]: starts_up = True; exits_down = True
            if row in [5, 6, 7, 8]: starts_down = True; exits_up = True
        elif sub == 8: # Двойные Хампти
            if row in [1, 2, 3, 4]: starts_up = True; exits_up = True
            if row in [5, 6, 7, 8]: starts_down = True; exits_down = True

    # 3. НАЗНАЧЕНИЕ СКОРОСТЕЙ
    if starts_up: req_speed = 'HS_REQ'
    elif starts_down: req_speed = 'LS_REQ'
    else: req_speed = 'MS_REQ'

    if exits_up: out_speed = 'LS'
    elif exits_down: out_speed = 'HS'
    else: out_speed = 'MS'

    if has_spin: req_speed = 'LS_REQ'

    changes_axis = does_figure_change_axis(aresti_list)
    is_complex = len(aresti_list) >= 3

    return {
        "family": family, "sub": sub, "base_code": base, "roll_codes": roll_codes,
        "out_speed": out_speed, "req_speed": req_speed,
        "req_entry": req_entry, "exit_att": exit_att,
        "is_complex": is_complex, "changes_axis": changes_axis, "has_spin": has_spin
    }

def is_clean_macro(macro, aresti_list):
    """Свирепый санитар. Уничтожает любой мусор."""
    m = macro.lower()
    if any(w in m for w in ["sequence", "generated", "unknown", "training", "unlimited", "free", "known"]): return False
    if not aresti_list or len(aresti_list[0].split('.')) < 4: return False
    
    m_let = re.sub(r'[^a-z]', '', m)
    if not m_let: return False 
    if aresti_list[0].startswith("1.1.1.") and len(aresti_list) < 2: return False

    has_spin = any(r.split('.')[1] in ['11', '12', '13'] for r in aresti_list[1:] if len(r.split('.')) == 4)
    if has_spin and 's' not in m_let: return False
    if 's' in m_let and not has_spin and not aresti_list[0].startswith('7.5.'): return False

    return True

# ИСПРАВЛЕННЫЕ ПАРАШЮТЫ (Теперь 100% правильно возвращают оси и скорости!)
def get_y_recovery_figure(att, speed):
    if speed == 'HS': return {"macro": "-h1-" if att == 'I' else "+h1+", "aresti": ["5.2.1.1", "9.1.5.1"] if att == 'U' else ["5.2.1.2", "9.1.5.1"], "req_speed": "HS_REQ", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "Y", "changes_axis": True, "is_complex": False, "has_spin": False, "base_code": "5.2.1.1", "roll_codes": ["9.1.5.1"], "family": 5, "sub": 2}
    elif speed == 'LS': return {"macro": "-v1-" if att == 'I' else "+v1+", "aresti": ["1.1.6.3", "9.1.5.1"] if att == 'U' else ["1.1.6.4", "9.1.5.1"], "req_speed": "LS_REQ", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "Y", "changes_axis": True, "is_complex": False, "has_spin": False, "base_code": "1.1.6.3", "roll_codes": ["9.1.5.1"], "family": 1, "sub": 1}
    else: return {"macro": "-1j-" if att == 'I' else "+1j+", "aresti": ["2.1.1.2"] if att == 'I' else ["2.1.1.1"], "req_speed": "MS_REQ", "out_speed": "MS", "req_entry": att, "exit_att": att, "axis": "Y", "changes_axis": True, "is_complex": False, "has_spin": False, "base_code": "2.1.1.1", "roll_codes": [], "family": 2, "sub": 1}

def get_x_recovery_figure(att, speed):
    if speed == 'HS': return {"macro": "-o-" if att == 'I' else "+o+", "aresti": ["7.4.2.1"] if att == 'I' else ["7.4.1.1"], "req_speed": "HS_REQ", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "X", "changes_axis": False, "is_complex": False, "has_spin": False, "base_code": "7.4.1.1", "roll_codes": [], "family": 7, "sub": 4}
    elif speed == 'LS': return {"macro": "-a+" if att == 'I' else "+2a+", "aresti": ["7.2.3.3"] if att == 'I' else ["7.2.3.3", "9.1.3.2"], "req_speed": "LS_REQ", "out_speed": "HS", "req_entry": att, "exit_att": "U", "axis": "X", "changes_axis": False, "is_complex": False, "has_spin": False, "base_code": "7.2.3.3", "roll_codes": [], "family": 7, "sub": 2}
    else: return {"macro": "-j-" if att == 'I' else "+j+", "aresti": ["2.2.1.2"] if att == 'I' else ["2.2.1.1"], "req_speed": "MS_REQ", "out_speed": "MS", "req_entry": att, "exit_att": att, "axis": "X", "changes_axis": False, "is_complex": False, "has_spin": False, "base_code": "2.2.1.1", "roll_codes": [], "family": 2, "sub": 2}

# ==========================================
# 2. ГЕНЕРАТОР КОМПЛЕКСОВ
# ==========================================
DATABASE = load_database()

def build_tournament_sequence(length):
    sequence = []
    current_att = "U"     
    current_speed = "MS"  
    current_axis = "X"    
    cons_complex = 0      
    used_bases = set()
    used_rolls = set()

    clean_pool = []
    for family, figs in DATABASE.items():
        for f in figs:
            if is_clean_macro(f["macro"], f["aresti"]):
                physics = analyze_figure(f)
                f.update(physics)
                clean_pool.append(f)

    if not clean_pool:
        st.error("В базе не осталось валидных фигур!")
        return []

    for i in range(length):
        # 1. ЖЕСТКАЯ ФИЗИКА (Склейка положений)
        valid_figs = [f for f in clean_pool if f["req_entry"] == current_att]

        # 2. АБСОЛЮТНЫЙ ЗАКОН СКОРОСТЕЙ (Устранена твоя 7 и 8 ошибка)
        speed_filtered = []
        for f in valid_figs:
            req = f["req_speed"]
            if current_speed == 'HS' and req == 'HS_REQ': speed_filtered.append(f)
            elif current_speed == 'LS' and req == 'LS_REQ': speed_filtered.append(f)
            # Из MS можно делать плоские фигуры (MS) или нырять вниз за скоростью (LS)
            elif current_speed == 'MS' and req in ['MS_REQ', 'LS_REQ']: speed_filtered.append(f)
        valid_figs = speed_filtered

        # 3. ЖЕСТКИЙ ЛОК ОСИ Y (Только простые Виражи, Хаммерхеды и Линии для возврата)
        if current_axis == "Y":
            y_figs = [f for f in valid_figs if f["changes_axis"] and not f["is_complex"] and f["family"] in [1, 2, 5]]
            valid_figs = y_figs

        # 4. СПАСЕНИЕ КОМПЛЕКСА (Идеальными парашютами)
        if not valid_figs:
            fig = get_y_recovery_figure(current_att, current_speed) if current_axis == "Y" else get_x_recovery_figure(current_att, current_speed)
            sequence.append(fig)
            current_att, current_speed, cons_complex = fig["exit_att"], fig["out_speed"], 0
            if current_axis == "Y": current_axis = "X"
            continue

        # 5. ФИЛЬТРЫ КОМФОРТА И CIVA (Нельзя уходить на Y в конце и повторять фигуры)
        strict_figs = []
        for f in valid_figs:
            if current_axis == "X" and f["changes_axis"] and i >= length - 2: continue 
            if cons_complex >= 2 and f["is_complex"]: continue
            if f["base_code"] in used_bases: continue 
            if any(r in used_rolls for r in f["roll_codes"]): continue 
            strict_figs.append(f)

        if strict_figs:
            fig = random.choice(strict_figs)
        else:
            f1 = [f for f in valid_figs if (current_axis == "Y" or not f["changes_axis"]) and f["base_code"] not in used_bases and not any(r in used_rolls for r in f["roll_codes"])]
            if f1: fig = random.choice(f1)
            else:
                f2 = [f for f in valid_figs if (current_axis == "Y" or not f["changes_axis"]) and f["base_code"] not in used_bases]
                if f2: fig = random.choice(f2)
                else: fig = random.choice(valid_figs)

        sequence.append({
            "macro": fig["macro"],
            "aresti": ", ".join(fig.get("aresti", [])),
            "speed_in": current_speed,
            "att_in": current_att,
            "att_out": fig["exit_att"],
            "axis": current_axis,
            "is_complex": fig["is_complex"],
            "has_spin": fig["has_spin"]
        })

        if "base_code" in fig:
            used_bases.add(fig["base_code"])
            used_rolls.update(fig["roll_codes"])

        # Обновление телеметрии
        current_att = fig["exit_att"] 
        current_speed = fig["out_speed"]
        if fig["changes_axis"]: current_axis = "Y" if current_axis == "X" else "X"
        cons_complex = cons_complex + 1 if fig["is_complex"] else 0

    return sequence

# --- Streamlit UI ---
st.set_page_config(page_title="Unlimited World Champ", page_icon="🏆")
st.title("🏆 Unlimited Pro (The Final Engine)")
st.write("Исправлены инверсии осей на 270-градусных виражах. Внедрена прямая и жесткая логика крейсерской скорости (MS). Идеальные аварийные маневры.")

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
        spin_txt = "🌀 **ШТОПОР**" if fig["has_spin"] else ""
        
        st.write(f"**{i+1}.** `{fig['macro']}` {spin_txt}")
        st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;*Вход:* {att_in} ({spd_icon}) ➡️ *Выход:* {att_out} | *Арести:* {fig.get('aresti', 'N/A')}")
