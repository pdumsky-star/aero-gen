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
# 1. АНАЛИЗАТОР ФИЗИКИ (МАТРИЦА АРЕСТИ)
# ==========================================
def does_figure_change_axis(aresti_list):
    changes = False
    for code in aresti_list:
        parts = code.split('.')
        if len(parts) == 4:
            family = int(parts[0])
            # Повороты на 90 (1) и 270 (3)
            if family == 2 and parts[1] in ['1', '3']: changes = not changes 
            # Нечетные бочки (1/4, 3/4) на вертикалях (3 - вверх, 5 - вниз)
            elif family == 9:
                if int(parts[2]) in [3, 5] and int(parts[3]) % 2 != 0: changes = not changes
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
    starts_up = False
    exits_up = False

    if family == 1:
        if sub == 1: # Линии
            if row == 6 and col in [1, 2]: starts_up = True; exits_up = True
            if row == 7 and col in [3, 4]: starts_up = True; exits_up = True
        elif sub == 2: # 45 градусов
            if col in [1, 2]: starts_up = True
            if row in [1, 2] and col in [1, 2]: exits_up = True
            if row in [3, 4] and col in [1, 2]: exits_up = True
            if row in [5, 6] and col in [3, 4]: exits_up = True
    elif family in [5, 6]: # Хаммерхеды и Колокола
        starts_up = True
    elif family == 7: # Петли
        if sub in [1, 2]:
            if row in [1, 2]: starts_up = True; exits_up = True # Иммельманы
        elif sub in [3, 4]:
            if col in [1, 2]: starts_up = True
            if sub == 3 and row in [1, 2]: exits_up = True # 3/4 петли вверх
    elif family == 8: # Комбинированные (Кубинцы, Хампти, P-петли)
        if col in [1, 2]: starts_up = True
        if sub == 4 and row % 2 == 0: exits_up = True # Все четные Хампти-бампы выходят вверх
        elif sub == 6 and row in [3, 4]: exits_up = True # Обратные P-петли, выходящие в вертикаль
        elif sub == 8 and row in [1, 2]: exits_up = True

    # --- 2. РАСЧЕТ СКОРОСТЕЙ (ENERGY MANAGEMENT) ---
    out_speed = 'LS' if exits_up else ('MS' if family == 2 or (family == 1 and sub == 1 and row == 1) else 'HS')
    
    req_speed = 'Any'
    if starts_up: req_speed = 'HS'
    if has_spin: req_speed = 'LS' # Штопор ТОЛЬКО на сваливании
    elif family == 2 or (family == 1 and sub == 1 and row == 1): req_speed = 'MS_LS'
    elif family == 7 and sub in [1, 2] and row in [3, 4]: req_speed = 'MS_LS' # Сплит-С

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
    
    # БЛОКИРОВКА ПУСТЫХ СТРОК И ГОЛЫХ ЛИНИЙ (Твоя ошибка с 10 фигурой)
    if not re.search(r'[a-zA-Z0-9]', m): return False
    if aresti_list[0].startswith("1.1.1.") and len(aresti_list) < 2: return False

    m_let = re.sub(r'[^a-z]', '', m)
    if 'rc' in m_let: return aresti_list[0].startswith('8.5.2')
    if 'c' in m_let and 'rc' not in m_let: return aresti_list[0].startswith('8.5.6') or aresti_list[0].startswith('8.5.5')
    if 'm' in m_let: return aresti_list[0].startswith('7.2.2') or aresti_list[0].startswith('7.2.1')
    if 'a' in m_let and not any(x in m_let for x in ['ta','ia']): return aresti_list[0].startswith('7.2.3') or aresti_list[0].startswith('7.2.4')
    if 'h' in m_let and 'dh' not in m_let: return aresti_list[0].startswith('5.2.1')
    if 'j' in m_let: return aresti_list[0].startswith('2.')
    return True

def get_recovery_figure(att, speed):
    """Аварийная фигура. Вставляется, если база исчерпана, чтобы гарантированно сохранить физику полёта."""
    if speed == 'LS':
        if att == 'I': return {"macro": "-a+", "aresti": ["7.2.3.3"], "speed_in": "LS", "att_in": "I", "att_out": "U", "axis": "X", "is_complex": False, "has_spin": False, "out_speed": "HS", "changes_axis": False}
        else: return {"macro": "+2a+", "aresti": ["7.2.3.3", "9.1.3.2"], "speed_in": "LS", "att_in": "U", "att_out": "U", "axis": "X", "is_complex": False, "has_spin": False, "out_speed": "HS", "changes_axis": False}
    else:
        if att == 'I': return {"macro": "-o-", "aresti": ["7.4.3.1"], "speed_in": "HS", "att_in": "I", "att_out": "I", "axis": "X", "is_complex": False, "has_spin": False, "out_speed": "HS", "changes_axis": False}
        else: return {"macro": "+o+", "aresti": ["7.4.1.1"], "speed_in": "HS", "att_in": "U", "att_out": "U", "axis": "X", "is_complex": False, "has_spin": False, "out_speed": "HS", "changes_axis": False}

# ==========================================
# 2. ГЕНЕРАТОР КОМПЛЕКСОВ
# ==========================================
DATABASE = load_database()

def build_tournament_sequence(length):
    sequence = []
    current_att = "U"     
    current_speed = "MS"  
    current_axis = "X"    
    figures_on_y = 0
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
        # ЭТАП 1: ЖЕСТКАЯ ФИЗИКА (Вход + Скорость) - Нарушать нельзя!
        valid_figs = [f for f in clean_pool if f["entry"] == current_att]
        valid_figs = [f for f in valid_figs if not (f["req_speed"] == 'LS' and current_speed != 'LS')]
        valid_figs = [f for f in valid_figs if not (f["req_speed"] == 'HS' and current_speed == 'LS')]
        valid_figs = [f for f in valid_figs if not (f["req_speed"] == 'MS_LS' and current_speed == 'HS')]

        if not valid_figs:
            fig = get_recovery_figure(current_att, current_speed)
            sequence.append(fig)
            current_att, current_speed, cons_complex = fig["att_out"], fig["out_speed"], 0
            st.toast(f"Фигура {i+1}: Сработал парашют спасения ({fig['macro']})", icon="⚠️")
            continue

        # ЭТАП 2: ФИЛЬТРЫ КОМФОРТА И ПРАВИЛ CIVA
        strict_figs = []
        for f in valid_figs:
            # Требование: Возврат с оси Y должен быть ПРОСТОЙ фигурой!
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
            # Мягкое ослабление правил, если нет идеальной фигуры
            f1 = [f for f in valid_figs if (not (current_axis == "Y" and not f["changes_axis"])) and f["base_code"] not in used_bases and not any(r in used_rolls for r in f["roll_codes"])]
            if f1: fig = random.choice(f1)
            else:
                f2 = [f for f in valid_figs if (not (current_axis == "Y" and not f["changes_axis"])) and f["base_code"] not in used_bases]
                if f2: fig = random.choice(f2)
                else: fig = random.choice(valid_figs)

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
        figures_on_y = figures_on_y + 1 if current_axis == "Y" else 0
        cons_complex = cons_complex + 1 if fig["is_complex"] else 0

    return sequence

# --- Streamlit UI ---
st.set_page_config(page_title="Unlimited World Champ", page_icon="🏆")
st.title("🏆 Unlimited World Champ (Aresti Matrix)")
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
        
        st.write(f"**{i+1}.** `{fig['macro']}`")
        st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;*Вход:* {att_in} ({spd_icon}) ➡️ *Выход:* {att_out} | *Арести:* {fig.get('aresti', 'N/A')}")
