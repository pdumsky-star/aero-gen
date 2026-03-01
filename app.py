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
# 1. АНАЛИЗАТОР ФИЗИКИ И СКОРОСТИ
# ==========================================
def does_figure_change_axis(aresti_list):
    changes = False
    for code in aresti_list:
        parts = code.split('.')
        if len(parts) == 4:
            family = int(parts[0])
            if family == 2 and parts[1] in ['1', '3']: changes = not changes 
            elif family == 9:
                line_dir = int(parts[2])
                amount = int(parts[3])
                if line_dir in [3, 5] and amount % 2 != 0: changes = not changes
    return changes

def analyze_figure(f_data):
    aresti_list = f_data["aresti"]
    base = aresti_list[0]
    parts = base.split('.')
    family = int(parts[0])
    sub = int(parts[1]) if len(parts) > 1 else 0
    row = int(parts[2]) if len(parts) > 2 else 0

    roll_codes = aresti_list[1:]
    has_spin = any(r.split('.')[1] in ['11', '12', '13'] for r in roll_codes if len(r.split('.')) == 4)
            
    # --- 1. РАСЧЕТ СКОРОСТИ НА ВЫХОДЕ (Теряет ли фигура энергию?) ---
    out_speed = 'HS' # По умолчанию выходим на скорости
    if family == 1 and sub == 1 and row == 6: out_speed = 'LS' # Вертикаль вверх
    if family == 1 and sub == 2 and row in [1, 2, 3, 4]: out_speed = 'LS' # 45 вверх
    if family == 7 and sub in [1, 2] and row in [1, 2]: out_speed = 'LS' # Иммельманы
    if family == 7 and sub == 3 and row in [1, 2]: out_speed = 'LS' # 3/4 петли вверх
    if family == 8 and sub == 6 and row in [1, 2, 3, 4]: out_speed = 'LS' # P-Loop (выход на вертикали)
    if family == 2: out_speed = 'MS' # Виражи

    # --- 2. РАСЧЕТ ТРЕБУЕМОЙ СКОРОСТИ (Нужно ли тянуть вверх?) ---
    starts_up = False
    if family == 1 and sub == 1 and row == 6: starts_up = True
    if family == 1 and sub == 2 and row in [1, 2, 3, 4]: starts_up = True
    if family in [5, 6]: starts_up = True # Хаммерхеды, Колокола
    if family == 7 and sub in [1, 2] and row in [1, 2]: starts_up = True
    if family == 7 and sub == 3 and row in [1, 2]: starts_up = True
    if family == 7 and sub == 4 and row in [1, 2]: starts_up = True # Прямые петли
    if family == 8:
        starts_up = True
        # Исключения: Хампти-Бампы и P-петли, начинающиеся вниз
        if sub == 4 and row in [5, 6, 7, 8]: starts_up = False 
        if sub == 6 and row in [3, 4]: starts_up = False 
    
    req_speed = 'Any'
    if starts_up: req_speed = 'HS'
    if has_spin: req_speed = 'LS'
    elif family == 2: req_speed = 'MS_LS'
    elif family == 7 and sub in [1, 2] and row in [3, 4]: req_speed = 'MS_LS'

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
    """Усиленный санитарный фильтр"""
    m = macro.lower()
    if any(w in m for w in ["sequence", "generated", "unknown", "training", "unlimited", "free", "known"]): return False
    if not aresti_list or len(aresti_list[0].split('.')) < 4: return False
    
    # ЗАЩИТА: Исключаем пустые макросы (например, состоящие только из минуса "-")
    if not re.search(r'[a-zA-Z0-9]', m): return False
    
    base = aresti_list[0]
    # ЗАЩИТА: Горизонтальные линии (1.1.1) ОБЯЗАНЫ иметь хотя бы одну бочку (иначе это просто линия)
    if base.startswith("1.1.1.") and len(aresti_list) < 2: return False

    m_let = re.sub(r'[^a-z]', '', m)
    if 'rc' in m_let: return base.startswith('8.5.2')
    if 'c' in m_let and 'rc' not in m_let: return base.startswith('8.5.6') or base.startswith('8.5.5')
    if 'm' in m_let: return base.startswith('7.2.2') or base.startswith('7.2.1')
    if 'a' in m_let and not any(x in m_let for x in ['ta','ia']): return base.startswith('7.2.3') or base.startswith('7.2.4')
    if 'h' in m_let and 'dh' not in m_let: return base.startswith('5.2.1')
    if 'j' in m_let: return base.startswith('2.')
    return True

def get_recovery_figure(att, speed):
    """Аварийная фигура-парашют. Применяется, если в базе закончились фигуры, 
    чтобы никогда не нарушать законы физики (LS/HS)."""
    if speed == 'LS':
        if att == 'I':
            # На спине без скорости -> Сплит-С
            return {"macro": "-a+", "aresti": "7.2.3.3", "speed_in": "LS", "att_in": "I", "att_out": "U", "axis": "X", "is_complex": False, "has_spin": False, "out_speed": "HS"}
        else:
            # На пузе без скорости -> Хампти-Бамп вниз
            return {"macro": "+b+", "aresti": "8.4.5.1", "speed_in": "LS", "att_in": "U", "att_out": "U", "axis": "X", "is_complex": False, "has_spin": False, "out_speed": "HS"}
    else:
        if att == 'I':
            # На спине на скорости -> Обратная петля
            return {"macro": "-o-", "aresti": "7.4.3.1", "speed_in": "HS", "att_in": "I", "att_out": "I", "axis": "X", "is_complex": False, "has_spin": False, "out_speed": "HS"}
        else:
            # На пузе на скорости -> Обычная петля
            return {"macro": "+o+", "aresti": "7.4.1.1", "speed_in": "HS", "att_in": "U", "att_out": "U", "axis": "X", "is_complex": False, "has_spin": False, "out_speed": "HS"}

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
        # ЭТАП 1: ЖЕСТКИЕ ЗАКОНЫ ФИЗИКИ (НЕЛЬЗЯ НАРУШАТЬ)
        valid_figs = [f for f in clean_pool if f["entry"] == current_att]
        valid_figs = [f for f in valid_figs if not (f["req_speed"] == 'LS' and current_speed != 'LS')]
        valid_figs = [f for f in valid_figs if not (f["req_speed"] == 'HS' and current_speed == 'LS')]
        valid_figs = [f for f in valid_figs if not (f["req_speed"] == 'MS_LS' and current_speed == 'HS')]

        if not valid_figs:
            # БАЗА ИСТОЩЕНА. Применяем аварийную физически корректную фигуру.
            fig = get_recovery_figure(current_att, current_speed)
            sequence.append(fig)
            current_att = fig["att_out"]
            current_speed = fig["out_speed"]
            cons_complex = 0
            st.toast(f"Фигура {i+1}: База исчерпана, вставлена аварийная спасательная фигура ({fig['macro']})", icon="⚠️")
            continue

        # ЭТАП 2: МЯГКИЕ ПРАВИЛА CIVA (Контроль перегрузки, осей и уникальности)
        strict_figs = []
        for f in valid_figs:
            if current_axis == "Y" and figures_on_y >= 1 and not f["changes_axis"]: continue 
            if current_axis == "X" and f["changes_axis"] and i >= length - 2: continue 
            if cons_complex >= 2 and (not f["is_turn"] or f["is_complex"]): continue
            if f["base_code"] in used_bases: continue 
            if any(r in used_rolls for r in f["roll_codes"]): continue 
            strict_figs.append(f)

        # Выбор фигуры с постепенным ослаблением правил, если база скудная
        if strict_figs:
            fig = random.choice(strict_figs)
        else:
            # Ослабление 1: Игнорируем оси и перегрузку, но требуем уникальность
            relaxed = [f for f in valid_figs if f["base_code"] not in used_bases and not any(r in used_rolls for r in f["roll_codes"])]
            if relaxed:
                fig = random.choice(relaxed)
            else:
                # Ослабление 2: Разрешаем повторить вращение
                relaxed = [f for f in valid_figs if f["base_code"] not in used_bases]
                if relaxed:
                    fig = random.choice(relaxed)
                else:
                    # Ослабление 3: Разрешаем повторить базу (полная капитуляция CIVA перед физикой)
                    fig = random.choice(valid_figs)

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

        # Обновление телеметрии
        current_att = fig["exit"] 
        current_speed = fig["out_speed"]
        
        if fig["changes_axis"]: current_axis = "Y" if current_axis == "X" else "X"
        if current_axis == "Y": figures_on_y += 1
        else: figures_on_y = 0
        
        cons_complex = cons_complex + 1 if fig["is_complex"] else 0

    return sequence

# --- Streamlit UI ---
st.set_page_config(page_title="Unlimited World Champ", page_icon="🏆")
st.title("🏆 Unlimited World Champ (Robust Physics)")
st.write("Теперь физика (LS/HS) железобетонна. Если в базе нет нужной фигуры, скрипт вставит аварийный маневр спасения.")

num_figs = st.sidebar.slider("Количество фигур", 5, 15, 10)

if st.button("Сгенерировать комплекс"):
    complex_data = build_tournament_sequence(num_figs)
    final_string = " ".join([fig["macro"] for fig in complex_data])
    
    st.success("✅ Готово! Копируй в OpenAero и нажимай **Separate figures**.")
    st.code(final_string, language="text")
    
    st.write("### Телеметрия и Память CIVA:")
    for i, fig in enumerate(complex_data):
        att_in = "⬆️ Пузо" if fig["att_in"] == "U" else "⬇️ Спина"
        att_out = "⬆️ Пузо" if fig["att_out"] == "U" else "⬇️ Спина"
        spd_icon = "🛑 Stall (LS)" if fig["speed_in"] == "LS" else ("🔥 Energy (HS)" if fig["speed_in"] == "HS" else "💨 Cruiser (MS)")
        
        st.write(f"**{i+1}.** `{fig['macro']}`")
        st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;*Вход:* {att_in} ({spd_icon}) ➡️ *Выход:* {att_out} | *Арести:* {fig.get('aresti', 'N/A')}")
