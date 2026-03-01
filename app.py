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
# 1. ФИЗИКА И СКОРОСТЬ
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
    """Анализирует скорость, сложность и смену осей (без угадывания переворотов)"""
    aresti_list = f_data["aresti"]
    base = aresti_list[0]
    family = int(base.split('.')[0])
    
    has_spin = False
    for code in aresti_list[1:]:
        rp = code.split('.')
        if len(rp) == 4 and rp[0] == '9' and rp[1] in ['11', '12', '13']:
            has_spin = True
            
    out_speed = 'HS'
    parts = base.split('.')
    sub = int(parts[1]) if len(parts)>1 else 0
    row = int(parts[2]) if len(parts)>2 else 0
    
    # После восходящих линий скорость падает (LS - Low Speed)
    if family == 1 and sub == 1 and row == 6: out_speed = 'LS' 
    if family == 1 and sub == 2 and row in [1, 2, 3, 4]: out_speed = 'LS'
    if family == 7 and sub == 2 and row in [1, 2]: out_speed = 'LS'
    if family == 8 and sub == 6 and row in [1, 2, 3, 4]: out_speed = 'LS'
    if family == 2 or (family == 1 and sub == 1 and row == 1): out_speed = 'MS'

    req_speed = 'Any'
    if has_spin: req_speed = 'LS' # Штопор только после сваливания
    elif family == 2 or (family == 1 and sub == 1 and row == 1): req_speed = 'MS_LS'
    elif family == 7 and sub == 2 and row in [3, 4]: req_speed = 'MS_LS'

    is_complex = len(aresti_list) >= 3
    is_turn = family in [5, 6, 8] or (family == 2 and sub == 2) or (family == 7 and sub == 2)
    changes_axis = does_figure_change_axis(aresti_list)

    return {
        "out_speed": out_speed, "req_speed": req_speed,
        "is_complex": is_complex, "is_turn": is_turn,
        "changes_axis": changes_axis, "has_spin": has_spin
    }

def is_clean_macro(macro, aresti_list):
    m = macro.lower()
    if any(w in m for w in ["sequence", "generated", "unknown", "training", "unlimited", "free", "known"]): return False
    if not aresti_list or len(aresti_list[0].split('.')) < 4: return False
    
    # Оставляем только буквы для санитарной проверки
    m_let = re.sub(r'[^a-z]', '', m)
    base = aresti_list[0]
    if 'rc' in m_let: return base.startswith('8.5.2')
    if 'c' in m_let and 'rc' not in m_let: return base.startswith('8.5.6') or base.startswith('8.5.5')
    if 'm' in m_let: return base.startswith('7.2.2') or base.startswith('7.2.1')
    if 'a' in m_let and not any(x in m_let for x in ['ta','ia']): return base.startswith('7.2.3') or base.startswith('7.2.4')
    if 'h' in m_let and 'dh' not in m_let: return base.startswith('5.2.1')
    if 'j' in m_let: return base.startswith('2.')
    return True

# ==========================================
# 2. ГЕНЕРАТОР КОМПЛЕКСОВ
# ==========================================
DATABASE = load_database()

def build_tournament_sequence(length):
    sequence = []
    current_att = "U"     # Начинаем с прямого полета (+)
    current_speed = "MS"  # Стартовая скорость средняя
    current_axis = "X"    # Главная ось
    
    figures_on_y = 0
    cons_complex = 0      # Счётчик сложных фигур

    clean_pool = []
    for family, figs in DATABASE.items():
        for f in figs:
            if is_clean_macro(f["macro"], f["aresti"]):
                physics = analyze_figure(f)
                f.update(physics)
                clean_pool.append(f)

    if not clean_pool:
        st.error("В базе не осталось валидных фигур! Проверьте civa_database.json")
        return []

    for i in range(length):
        valid_figs = []
        for f in clean_pool:
            # Правило 1: ИДЕАЛЬНАЯ СКЛЕЙКА (Выход предыдущей = Вход текущей)
            if f["entry"] != current_att: continue
            
            # Правило 2: Скорость (Штопоры только на LS)
            if f["req_speed"] == 'LS' and current_speed != 'LS': continue
            if f["req_speed"] == 'MS_LS' and current_speed == 'HS': continue
            
            # Правило 3: Защита от перегрузки сложных фигур
            if cons_complex >= 2 and (not f["is_turn"] or f["is_complex"]): continue

            # Правило 4: Защита поперечной оси
            if current_axis == "Y" and figures_on_y >= 1 and not f["changes_axis"]: continue 
            if current_axis == "X" and f["changes_axis"] and i >= length - 2: continue 

            valid_figs.append(f)

        # Failsafe
        if not valid_figs:
            valid_figs = [f for f in clean_pool if f["entry"] == current_att and (f["req_speed"] != 'LS' or current_speed == 'LS')]

        if not valid_figs: 
            st.warning(f"Остановка сборки: нет маневра для входа {'со спины' if current_att == 'I' else 'прямо'} при скорости {current_speed}.")
            break

        fig = random.choice(valid_figs)

        sequence.append({
            "macro": fig["macro"],
            "aresti": ", ".join(fig["aresti"]),
            "speed_in": current_speed,
            "att_in": current_att,
            "att_out": fig["exit"],
            "axis": current_axis,
            "is_complex": fig["is_complex"],
            "has_spin": fig["has_spin"]
        })

        # --- ОБНОВЛЕНИЕ ТЕЛЕМЕТРИИ ---
        current_att = fig["exit"] # Выход этой фигуры становится входом для следующей!
        current_speed = fig["out_speed"]
        
        if fig["changes_axis"]: current_axis = "Y" if current_axis == "X" else "X"
        if current_axis == "Y": figures_on_y += 1
        else: figures_on_y = 0
        
        cons_complex = cons_complex + 1 if fig["is_complex"] else 0

    return sequence

# --- Streamlit UI ---
st.set_page_config(page_title="Unlimited PRO", page_icon="✈️")
st.title("🏆 Unlimited Pro (Native Tracking)")
st.write("Идеальная склейка фигур по нативным маркерам `+` и `-` из языка OLAN.")

num_figs = st.sidebar.slider("Количество фигур", 5, 15, 10)

if st.button("Сгенерировать комплекс"):
    complex_data = build_tournament_sequence(num_figs)
    final_string = " ".join([fig["macro"] for fig in complex_data])
    
    st.success("✅ Готово! Копируй в OpenAero и нажимай **Separate figures**.")
    st.code(final_string, language="text")
    
    st.write("### Телеметрия полета:")
    for i, fig in enumerate(complex_data):
        att_in = "⬆️ Прямой" if fig["att_in"] == "U" else "⬇️ На спине"
        att_out = "⬆️ Прямой" if fig["att_out"] == "U" else "⬇️ На спине"
        spd_icon = "🛑 Сваливание" if fig["speed_in"] == "LS" else ("🔥 Пикирование" if fig["speed_in"] == "HS" else "💨 Средняя")
        spin_txt = "🌀 **ШТОПОР**" if fig["has_spin"] else ""
        
        st.write(f"**{i+1}.** `{fig['macro']}` {spin_txt}")
        st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;*Вход:* {att_in} ➡️ *Выход:* {att_out} | Скорость: {spd_icon}")
