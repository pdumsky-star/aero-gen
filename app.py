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
# 1. АНАЛИЗАТОР ФИЗИКИ (МАТРИЦА HS/MS/LS)
# ==========================================
def does_figure_change_axis(aresti_list):
    changes = False
    for code in aresti_list:
        parts = code.split('.')
        if len(parts) == 4:
            family = int(parts[0])
            if family == 2 and parts[1] in ['1', '3', '5']: changes = not changes 
            elif family == 9 and int(parts[2]) in [3, 5] and int(parts[3]) % 2 != 0: changes = not changes
    return changes

def analyze_figure(f_data):
    aresti_list = f_data["aresti"]
    base = aresti_list[0]
    parts = base.split('.')
    family = int(parts[0])
    sub = int(parts[1]) if len(parts) > 1 else 0
    row = int(parts[2]) if len(parts) > 2 else 0
    col = int(parts[3]) if len(parts) > 3 else 0

    roll_codes = aresti_list[1:]
    has_spin = any(r.split('.')[1] in ['11', '12', '13'] for r in roll_codes if len(r.split('.')) == 4)

    # 1. ПОЛОЖЕНИЕ НА ВХОДЕ (Upright / Inverted)
    if family == 7 and sub == 2 and row in [3, 4]: req_entry = 'U' if col in [1, 4] else 'I'
    elif family == 1 and sub == 1 and row == 1: req_entry = 'U' if col in [1, 3] else 'I'
    else: req_entry = 'U' if col in [1, 3] else 'I'

    base_flip = False
    if family == 7 and sub == 2: base_flip = True
    if family == 8 and sub == 5: base_flip = True

    roll_flips = 0
    for code in roll_codes:
        rp = code.split('.')
        if len(rp) == 4 and rp[0] == '9':
            if int(rp[3]) in [2, 6]: roll_flips += 1 # Половинчатые бочки переворачивают самолет

    net_flip = base_flip ^ (roll_flips % 2 != 0)

    # 2. МАТРИЦА СКОРОСТЕЙ (HS / MS / LS)
    req_speed = 'MS_REQ'
    out_speed = 'MS'

    if family == 2:
        req_speed = 'MS_REQ'; out_speed = 'MS'
    elif family in [5, 6]:
        req_speed = 'HS_REQ'; out_speed = 'HS'
    elif family == 7:
        if sub in [1, 2]: # Полупетли
            if row in [1, 2]: req_speed = 'HS_REQ'; out_speed = 'LS'
            if row in [3, 4]: req_speed = 'LS_REQ'; out_speed = 'HS'
        elif sub == 3: # 3/4 петли
            if row in [1, 2]: req_speed = 'HS_REQ'; out_speed = 'HS'
            if row in [3, 4]: req_speed = 'LS_REQ'; out_speed = 'LS'
        elif sub in [4, 5]: # Полные петли
            if row in [1, 2, 5]: req_speed = 'HS_REQ'; out_speed = 'HS'
            if row in [3, 4, 6]: req_speed = 'LS_REQ'; out_speed = 'LS' # Петли вниз гасят скорость!
    elif family == 8:
        if sub in [1, 2, 3, 4, 13, 14, 15, 16, 17, 18]: # Хампти
            if row in [1, 2, 3, 4]: req_speed = 'HS_REQ'; out_speed = 'HS'
            if row in [5, 6, 7, 8]: req_speed = 'LS_REQ'; out_speed = 'LS'
        elif sub == 5: # Кубинцы
            if row in [1, 2, 3, 4]: req_speed = 'HS_REQ'; out_speed = 'HS'
            if row in [5, 6, 7, 8]: req_speed = 'LS_REQ'; out_speed = 'LS'
        elif sub == 6: # P-петли
            if row in [1, 2, 3, 4]: req_speed = 'HS_REQ'; out_speed = 'MS'
            if row in [5, 6, 7, 8]: req_speed = 'LS_REQ'; out_speed = 'MS'
        elif sub == 8: # Двойные Хампти
            if row in [1, 2, 3, 4]: req_speed = 'HS_REQ'; out_speed = 'LS'
            if row in [5, 6, 7, 8]: req_speed = 'LS_REQ'; out_speed = 'HS'
    elif family == 1:
        if sub == 1:
            if row == 1: req_speed = 'MS_REQ'; out_speed = 'MS'
            elif row in [2, 3, 4]: # 45 линий
                req_speed = 'HS_REQ' if col in [1, 2] else 'LS_REQ'
                out_speed = 'LS' if col in [1, 2] else 'HS'
            elif row in [6, 7]: # Вертикали
                req_speed = 'HS_REQ' if col in [1, 2] else 'LS_REQ'
                out_speed = 'LS' if col in [1, 2] else 'HS'
        elif sub == 2:
            if row in [1, 2, 3, 4]: req_speed = 'HS_REQ'; out_speed = 'MS'
            if row in [5, 6, 7, 8]: req_speed = 'LS_REQ'; out_speed = 'MS'
            if row in [9, 10, 11, 12]: req_speed = 'MS_REQ'; out_speed = 'LS'
            if row in [13, 14, 15, 16]: req_speed = 'MS_REQ'; out_speed = 'HS'
        elif sub == 3:
            if row in [1, 2, 3, 4]: req_speed = 'HS_REQ'; out_speed = 'LS'
            if row in [5, 6, 7, 8]: req_speed = 'LS_REQ'; out_speed = 'HS'
            if row in [9, 10, 11, 12]: req_speed = 'MS_REQ'; out_speed = 'MS'
            if row in [13, 14, 15, 16]: req_speed = 'MS_REQ'; out_speed = 'MS'

    if has_spin: req_speed = 'LS_REQ' # Штопор всегда требует сваливания

    changes_axis = does_figure_change_axis(aresti_list)
    is_complex = len(aresti_list) >= 3
    is_turn = family in [5, 6, 8] or (family == 2 and sub == 2) or (family == 7 and sub == 2)

    return {
        "base_code": base, "roll_codes": roll_codes,
        "out_speed": out_speed, "req_speed": req_speed,
        "req_entry": req_entry, "net_flip": net_flip,
        "is_complex": is_complex, "is_turn": is_turn,
        "changes_axis": changes_axis, "has_spin": has_spin
    }

def is_clean_macro(macro, aresti_list):
    """Свирепый фильтр макросов. Удаляет любой рассинхрон парсера!"""
    m = macro.lower()
    if any(w in m for w in ["sequence", "generated", "unknown", "training", "unlimited", "free", "known"]): return False
    if not aresti_list or len(aresti_list[0].split('.')) < 4: return False
    
    m_let = re.sub(r'[^a-z]', '', m)
    if not m_let: return False 
    
    base = aresti_list[0]
    fam = int(base.split('.')[0])
    sub = int(base.split('.')[1]) if len(base.split('.')) > 1 else 0
    if base.startswith("1.1.1.") and len(aresti_list) < 2: return False

    # СТРОГАЯ ЗАЩИТА: Синхронизация букв и семейств Арести
    has_spin = any(r.split('.')[1] in ['11', '12', '13'] for r in aresti_list[1:] if len(r.split('.')) == 4)
    if has_spin and 's' not in m_let and 'f' not in m_let: return False
    if 's' in m_let and not has_spin: return False

    if fam == 2 and 'j' not in m_let: return False
    if 'j' in m_let and fam not in [1, 2]: return False

    if fam == 5 and 'h' not in m_let: return False
    if fam == 6 and 't' not in m_let: return False
    if fam == 7 and not any(x in m_let for x in ['o', 'm', 'a', 'q', 'c']): return False

    if fam == 8:
        if sub == 6 and 'p' not in m_let: return False
        if sub == 5 and 'c' not in m_let: return False
        if sub in [4, 8] and 'b' not in m_let: return False

    return True

def get_recovery_figure(att, speed):
    """Парашют. Идеально подстраивается под MS/HS/LS."""
    if speed == 'HS':
        if att == 'I': return {"macro": "-o-", "aresti": ["7.4.2.1"], "req_speed": "HS_REQ", "out_speed": "HS", "req_entry": "I", "net_flip": False, "axis": "X", "changes_axis": False, "is_complex": False, "has_spin": False, "base_code": "7.4.2.1", "roll_codes": []}
        else: return {"macro": "+o+", "aresti": ["7.4.1.1"], "req_speed": "HS_REQ", "out_speed": "HS", "req_entry": "U", "net_flip": False, "axis": "X", "changes_axis": False, "is_complex": False, "has_spin": False, "base_code": "7.4.1.1", "roll_codes": []}
    elif speed == 'LS':
        if att == 'I': return {"macro": "-a+", "aresti": ["7.2.3.3"], "req_speed": "LS_REQ", "out_speed": "HS", "req_entry": "I", "net_flip": True, "axis": "X", "changes_axis": False, "is_complex": False, "has_spin": False, "base_code": "7.2.3.3", "roll_codes": []}
        else: return {"macro": "+2a+", "aresti": ["7.2.3.3", "9.1.3.2"], "req_speed": "LS_REQ", "out_speed": "HS", "req_entry": "U", "net_flip": False, "axis": "X", "changes_axis": False, "is_complex": False, "has_spin": False, "base_code": "7.2.3.3", "roll_codes": ["9.1.3.2"]}
    else: # MS
        if att == 'I': return {"macro": "-2j-", "aresti": ["2.1.3.1", "9.1.3.2"], "req_speed": "MS_REQ", "out_speed": "MS", "req_entry": "I", "net_flip": False, "axis": "X", "changes_axis": False, "is_complex": False, "has_spin": False, "base_code": "2.1.3.1", "roll_codes": ["9.1.3.2"]}
        else: return {"macro": "+j+", "aresti": ["2.1.3.1"], "req_speed": "MS_REQ", "out_speed": "MS", "req_entry": "U", "net_flip": False, "axis": "X", "changes_axis": False, "is_complex": False, "has_spin": False, "base_code": "2.1.3.1", "roll_codes": []}

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
        # ЭТАП 1: ЖЕСТКАЯ ФИЗИКА
        valid_figs = [f for f in clean_pool if f["req_entry"] in ['Any', current_att]]
        
        # 3-позиционная логика скорости
        valid_figs = [f for f in valid_figs if not (current_speed == 'HS' and f["req_speed"] != 'HS_REQ')]
        valid_figs = [f for f in valid_figs if not (current_speed == 'LS' and f["req_speed"] != 'LS_REQ')]
        # Если current_speed == 'MS', разрешены любые фигуры (летчик набирает или сбрасывает скорость)

        if not valid_figs:
            fig = get_recovery_figure(current_att, current_speed)
            sequence.append(fig)
            current_att = "I" if (current_att == "U" and fig["net_flip"]) or (current_att == "I" and not fig["net_flip"]) else "U"
            current_speed, cons_complex = fig["out_speed"], 0
            if current_axis == "Y": current_axis = "X" 
            continue

        # ЭТАП 2: ФИЛЬТРЫ ОСЕЙ И ПРАВИЛ CIVA
        strict_figs = []
        for f in valid_figs:
            # ЖЕСТКИЙ ВОЗВРАТ С ОСИ Y
            if current_axis == "Y":
                if not f["changes_axis"]: continue 
                if f["is_complex"]: continue # Возврат должен быть простым!
                # Разрешаем только читаемые с земли развороты
                if f["base_code"].split('.')[0] not in ['2', '5', '6', '8']: continue
                if f["base_code"].startswith('8.') and f["base_code"].split('.')[1] not in ['4', '5']: continue # Только Хампти/Кубинцы
            else:
                if f["changes_axis"] and i >= length - 2: continue 

            if cons_complex >= 2 and (not f["is_turn"] or f["is_complex"]): continue
            if f["base_code"] in used_bases: continue 
            if any(r in used_rolls for r in f["roll_codes"]): continue 
            strict_figs.append(f)

        if strict_figs:
            fig = random.choice(strict_figs)
        else:
            f1 = [f for f in valid_figs if (not (current_axis == "Y" and not f["changes_axis"])) and f["base_code"] not in used_bases and not any(r in used_rolls for r in f["roll_codes"])]
            if f1: fig = random.choice(f1)
            else:
                f2 = [f for f in valid_figs if (not (current_axis == "Y" and not f["changes_axis"])) and f["base_code"] not in used_bases]
                if f2: fig = random.choice(f2)
                else: 
                    f3 = [f for f in valid_figs if f["changes_axis"]] if current_axis == "Y" else valid_figs
                    if not f3: f3 = [get_recovery_figure(current_att, current_speed)]
                    fig = random.choice(f3)

        sequence.append({
            "macro": fig["macro"],
            "aresti": ", ".join(fig.get("aresti", [])),
            "speed_in": current_speed,
            "att_in": current_att,
            "axis": current_axis,
            "is_complex": fig["is_complex"],
            "has_spin": fig["has_spin"]
        })

        if "base_code" in fig:
            used_bases.add(fig["base_code"])
            used_rolls.update(fig["roll_codes"])

        current_att = "I" if (current_att == "U" and fig["net_flip"]) or (current_att == "I" and not fig["net_flip"]) else "U"
        current_speed = fig["out_speed"]
        if fig["changes_axis"]: current_axis = "Y" if current_axis == "X" else "X"
        cons_complex = cons_complex + 1 if fig["is_complex"] else 0

    return sequence

# --- Streamlit UI ---
st.set_page_config(page_title="Unlimited World Champ", page_icon="🏆")
st.title("🏆 Unlimited Pro (HS/MS/LS Physics)")
st.write("Скрипт идеально понимает разницу между крейсерской скоростью (MS) и пикированием (HS). Встроен жесткий санитарный контроль макросов.")

num_figs = st.sidebar.slider("Количество фигур", 5, 15, 10)

if st.button("Сгенерировать комплекс"):
    complex_data = build_tournament_sequence(num_figs)
    final_string = " ".join([fig["macro"] for fig in complex_data])
    
    st.success("✅ Готово! Копируй в OpenAero и нажимай **Separate figures**.")
    st.code(final_string, language="text")
    
    st.write("### Телеметрия:")
    for i, fig in enumerate(complex_data):
        att_in = "⬆️ Прямо" if fig["att_in"] == "U" else "⬇️ Спина"
        spd_icon = "🛑 Stall (LS)" if fig["speed_in"] == "LS" else ("🔥 Energy (HS)" if fig["speed_in"] == "HS" else "💨 Cruiser (MS)")
        spin_txt = "🌀 **ШТОПОР**" if fig["has_spin"] else ""
        
        st.write(f"**{i+1}.** `{fig['macro']}` {spin_txt}")
        st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;*Вход:* {att_in} ({spd_icon}) | *Арести:* {fig.get('aresti', 'N/A')}")
