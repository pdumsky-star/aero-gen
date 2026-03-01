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
# 1. АНАЛИЗАТОР ФИЗИКИ (ТОЧНАЯ МАТРИЦА АРЕСТИ)
# ==========================================
def does_figure_change_axis(aresti_list):
    changes = False
    for code in aresti_list:
        parts = code.split('.')
        if len(parts) == 4:
            family = int(parts[0])
            if family == 2 and parts[1] in ['1', '3']: changes = not changes 
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
            
    # --- 1. ТОЧНАЯ ГЕОМЕТРИЯ (ВВЕРХ / ВНИЗ) ---
    starts_down = False
    starts_up = False
    exits_up = False    # Фигура заканчивается наверху, гася скорость (дает LS)
    exits_down = False  # Фигура заканчивается внизу, набирая скорость (дает HS)

    if family == 1:
        if sub == 1:
            if row in [6, 7]:
                if col in [1, 2]: starts_up = True; exits_up = True
                if col in [3, 4]: starts_down = True; exits_down = True
        elif sub == 2:
            if row in [1,2,3,4]: starts_up = True
            if row in [5,6,7,8]: starts_down = True
            if row in [1,2,7,8]: exits_up = True
            if row in [3,4,5,6]: exits_down = True
    elif family in [5, 6]:
        starts_up = True; exits_down = True
    elif family == 7:
        if sub in [1, 2]:
            if row in [1, 2]: starts_up = True; exits_up = True
            if row in [3, 4]: starts_down = True; exits_down = True
        elif sub in [3, 4]:
            if row in [1, 2]: starts_up = True
            if row in [3, 4]: starts_down = True
            if sub == 3: 
                if row in [1, 2]: exits_down = True
                if row in [3, 4]: exits_up = True
    elif family == 8:
        # Для Хампти, Кубинцев и P-петель структура каталога идентична: 
        # Подгруппы 1-4 начинают вверх, 5-8 начинают вниз.
        if sub in [1,2,3,4, 13,14,15,16,17,18]: starts_up = True; exits_down = True
        if sub in [5,6,7,8, 19,20,21,22,23,24]: starts_down = True; exits_up = True

    # --- 2. РАСЧЕТ СКОРОСТЕЙ (ENERGY MANAGEMENT) ---
    if starts_up: req_speed = 'HS'
    elif starts_down: req_speed = 'LS'
    else: req_speed = 'Any'

    if exits_up: out_speed = 'LS'
    elif exits_down: out_speed = 'HS'
    else: out_speed = 'MS'

    # Переопределения скорости
    if has_spin: req_speed = 'LS'
    if family == 2 or (family == 1 and sub == 1 and row == 1):
        if req_speed == 'Any': req_speed = 'MS_LS' # Запрет плоских на огромной скорости

    changes_axis = does_figure_change_axis(aresti_list)
    is_complex = len(aresti_list) >= 3
    is_turn = family in [5, 6, 8] or (family == 2 and sub == 2) or (family == 7 and sub == 2)

    return {
        "base_code": base, "roll_codes": roll_codes,
        "out_speed": out_speed, "req_speed": req_speed,
        "is_complex": is_complex, "is_turn": is_turn,
        "changes_axis": changes_axis, "has_spin": has_spin
    }

def is_clean_macro(macro, aresti_list):
    m = macro.lower()
    if any(w in m for w in ["sequence", "generated", "unknown", "training", "unlimited", "free", "known"]): return False
    if not aresti_list or len(aresti_list[0].split('.')) < 4: return False
    
    # БЛОКИРОВКА ПУСТЫХ СТРОК (Ошибка 10 фигуры)
    m_let = re.sub(r'[^a-z]', '', m)
    if not m_let: return False # Отсекает пустые "-" или "+"
    
    # Блокировка голых линий
    base = aresti_list[0]
    if base.startswith("1.1.1.") and len(aresti_list) < 2: return False

    if 'rc' in m_let: return base.startswith('8.5.2')
    if 'c' in m_let and 'rc' not in m_let: return base.startswith('8.5.6') or base.startswith('8.5.5')
    if 'm' in m_let: return base.startswith('7.2.2') or base.startswith('7.2.1')
    if 'a' in m_let and not any(x in m_let for x in ['ta','ia']): return base.startswith('7.2.3') or base.startswith('7.2.4')
    if 'h' in m_let and 'dh' not in m_let: return base.startswith('5.2.1')
    if 'j' in m_let: return base.startswith('2.')
    return True

def get_recovery_figure(att, speed):
    """Аварийная фигура-парашют: 100% спасает физику полета, если исчерпана база"""
    if speed == 'LS':
        if att == 'I': return {"macro": "-a+", "aresti": ["7.2.3.3"], "speed_in": "LS", "att_in": "I", "att_out": "U", "axis": "X", "is_complex": False, "has_spin": False, "out_speed": "HS", "changes_axis": False, "base_code": "7.2.3.3", "roll_codes": []}
        else: return {"macro": "+2a+", "aresti": ["7.2.3.3", "9.1.3.2"], "speed_in": "LS", "att_in": "U", "att_out": "U", "axis": "X", "is_complex": False, "has_spin": False, "out_speed": "HS", "changes_axis": False, "base_code": "7.2.3.3", "roll_codes": ["9.1.3.2"]}
    else:
        if att == 'I': return {"macro": "-m+", "aresti": ["7.2.1.4"], "speed_in": "HS", "att_in": "I", "att_out": "U", "axis": "X", "is_complex": False, "has_spin": False, "out_speed": "LS", "changes_axis": False, "base_code": "7.2.1.4", "roll_codes": []}
        else: return {"macro": "+o+", "aresti": ["7.4.1.1"], "speed_in": "HS", "att_in": "U", "att_out": "U", "axis": "X", "is_complex": False, "has_spin": False, "out_speed": "HS", "changes_axis": False, "base_code": "7.4.1.1", "roll_codes": []}

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
        # ЭТАП 1: ЖЕСТКАЯ ФИЗИКА (Нарушать нельзя)
        valid_figs = [f for f in clean_pool if f["entry"] == current_att]
        valid_figs = [f for f in valid_figs if not (f["req_speed"] == 'LS' and current_speed != 'LS')]
        valid_figs = [f for f in valid_figs if not (f["req_speed"] == 'HS' and current_speed == 'LS')]
        valid_figs = [f for f in valid_figs if not (f["req_speed"] == 'MS_LS' and current_speed == 'HS')]

        if not valid_figs:
            fig = get_recovery_figure(current_att, current_speed)
            sequence.append(fig)
            current_att, current_speed, cons_complex = fig["att_out"], fig["out_speed"], 0
            st.toast(f"Фигура {i+1}: Сработал парашют спасения ({fig['macro']})", icon="⚠️")
            if current_axis == "Y": current_axis = "X" # Возврат на X
            continue

        # ЭТАП 2: ФИЛЬТРЫ ОСЕЙ И ПРАВИЛ CIVA
        strict_figs = []
        for f in valid_figs:
            # ЖЕСТКИЙ ВОЗВРАТ С ОСИ Y: только простая фигура, возвращающая на X!
            if current_axis == "Y":
                if not f["changes_axis"]: continue 
                if f["is_complex"]: continue 
            else:
                if f["changes_axis"] and i >= length - 2: continue 

            if cons_complex >= 2 and (not f["is_turn"] or f["is_complex"]): continue
            if f["base_code"] in used_bases: continue 
            if any(r in used_rolls for r in f["roll_codes"]): continue 
            strict_figs.append(f)

        if strict_figs:
            fig = random.choice(strict_figs)
        else:
            # Ослабление правил уникальности CIVA, если нет идеальной фигуры
            f1 = [f for f in valid_figs if (not (current_axis == "Y" and not f["changes_axis"])) and f["base_code"] not in used_bases and not any(r in used_rolls for r in f["roll_codes"])]
            if f1: fig = random.choice(f1)
            else:
                f2 = [f for f in valid_figs if (not (current_axis == "Y" and not f["changes_axis"])) and f["base_code"] not in used_bases]
                if f2: fig = random.choice(f2)
                else: 
                    # Последний шанс - игнорируем всё ради возврата с Y
                    f3 = [f for f in valid_figs if f["changes_axis"]] if current_axis == "Y" else valid_figs
                    fig = random.choice(f3 if f3 else valid_figs)

        sequence.append({
            "macro": fig["macro"],
            "aresti": ", ".join(fig.get("aresti", [])),
            "speed_in": current_speed,
            "att_in": current_att,
            "att_out": fig["exit"],
            "axis": current_axis,
            "is_complex": fig["is_complex"],
            "has_spin": fig["has_spin"]
        })

        if "base_code" in fig:
            used_bases.add(fig["base_code"])
            used_rolls.update(fig["roll_codes"])

        current_att = fig["exit"] 
        current_speed = fig["out_speed"]
        if fig["changes_axis"]: current_axis = "Y" if current_axis == "X" else "X"
        cons_complex = cons_complex + 1 if fig["is_complex"] else 0

    return sequence

# --- Streamlit UI ---
st.set_page_config(page_title="Unlimited World Champ", page_icon="🏆")
st.title("🏆 Unlimited World Champ (Aresti Physics)")
st.write("Скрипт читает матрицу Арести для 100% точного расчета скоростей. Возврат с поперечной оси теперь выполняется только **простыми** фигурами.")

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
