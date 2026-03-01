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
# 1. ФИЗИЧЕСКИЙ ДВИЖОК (АНАЛИЗАТОР АРЕСТИ)
# ==========================================
def analyze_figure_physics(aresti_list):
    """Вычисляет все аэродинамические свойства фигуры на основе кодов Арести"""
    base = aresti_list[0]
    family = int(base.split('.')[0])
    
    # 1. Положение (Attitude: Entry & Flip)
    req_entry = 'Any'
    base_flip = False
    
    # Требуют перевернутого входа (Сплиты, нисходящие петли, нисходящие кубинцы)
    if base.startswith(('7.2.3', '7.2.4', '8.5.5', '8.5.6', '8.5.7', '8.5.8', '7.4.4', '7.4.5', '7.4.6')):
        req_entry = 'I'
    # Требуют прямого входа (Иммельманы, восходящие петли, обычные/обратные кубинцы)
    elif base.startswith(('7.2.1', '7.2.2', '8.5.1', '8.5.2', '8.5.3', '8.5.4', '7.4.1', '7.4.2', '7.4.3')):
        req_entry = 'U'
        
    # Базовая геометрия переворачивает самолет? (Полупетли, Кубинцы)
    if base.startswith('7.2') or base.startswith('8.5'):
        base_flip = True

    # Считаем бочки, которые переворачивают самолет (на горизонталях и 45 градусах)
    roll_flips = 0
    has_spin = False
    changes_axis = False
    
    for code in aresti_list[1:]:
        rp = code.split('.')
        if len(rp) == 4 and rp[0] == '9':
            if rp[1] in ['11', '12']: has_spin = True
            
            b_line = int(rp[2]) # 1=horiz, 2=45up, 3=vert-up, 4=45down, 5=vert-down
            c_rot = int(rp[3])  # 2=1/2, 4=1/1, 6=1.5
            
            # Половинчатые вращения на горизонталях/45 линиях переворачивают самолет
            if b_line in [1, 2, 4] and c_rot in [2, 6]:
                roll_flips += 1
            # Нечетные вращения на вертикалях меняют ось (Y-box)
            if b_line in [3, 5] and c_rot % 2 != 0:
                changes_axis = not changes_axis

    # Итоговое изменение положения: База XOR Бочки
    net_flip = base_flip ^ (roll_flips % 2 != 0)

    # 2. Скорость (Speed Management)
    out_speed = 'HS' # По умолчанию выходим на большой скорости
    req_speed = 'Any'
    
    # Выходим на минимальной скорости (LS) после вертикалей вверх или Иммельманов
    if base.startswith(('7.2.1', '7.2.2', '1.2.1', '1.2.2', '1.2.3', '1.2.4')):
        out_speed = 'LS'
    # Выходим на средней (MS) после виражей или горизонтальных пролетов
    elif base.startswith('2.') or base.startswith('1.1.1'):
        out_speed = 'MS'

    # Штопор требует минимальной скорости (сваливания)
    if has_spin: 
        req_speed = 'LS'
    # Плоские маневры и Сплит-С запрещены на огромной скорости
    elif base.startswith(('2.', '1.1.1', '7.2.3', '7.2.4')): 
        req_speed = 'MS_LS'

    # 3. Сложность и Направление (Flow Control)
    is_complex = len(aresti_list) >= 3 # Считаем сложной, если 2 и более вращений
    is_turnaround = False
    # Фигуры, которые разворачивают самолет на 180 градусов
    if family in [5, 6] or base.startswith(('2.2', '7.2', '8.4', '8.5', '8.6')):
        is_turnaround = True

    return {
        "req_entry": req_entry, "net_flip": net_flip, 
        "out_speed": out_speed, "req_speed": req_speed,
        "is_complex": is_complex, "is_turn": is_turnaround,
        "changes_axis": changes_axis, "has_spin": has_spin
    }

# Санитарный фильтр для удаления ошибок парсера
def is_native_default(macro, aresti_list):
    m = macro.lower()
    if any(w in m for w in ["sequence", "generated", "unknown", "training", "unlimited", "free", "known"]): return False
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

def build_aerodynamic_data_sequence(length):
    sequence = []
    
    # Стартовые условия турнирного полета
    current_att = "U"     # Начинаем пузом вниз
    current_speed = "MS"  # Стартовая скорость средняя
    current_axis = "X"    # Главная ось
    
    figures_on_y = 0
    cons_complex = 0      # Счетчик сложных фигур подряд

    # 1. Готовим и анализируем базу
    clean_pool = []
    for family, figs in DATABASE.items():
        for f in figs:
            if is_native_default(f["macro"], f["aresti"]):
                physics = analyze_figure_physics(f["aresti"])
                f.update(physics)
                clean_pool.append(f)

    if not clean_pool:
        st.error("В базе не осталось валидных фигур!")
        return []

    # 2. Интеллектуальная сборка
    for i in range(length):
        valid_figs = []
        for f in clean_pool:
            # Правило 1: Ориентация (Attitude) - Поддерживаем Inverted полет!
            if f["req_entry"] != 'Any' and f["req_entry"] != current_att: continue
            
            # Правило 2: Скорость (Спин только на LS, запрет плоских на HS)
            if f["req_speed"] == 'LS' and current_speed != 'LS': continue
            if f["req_speed"] == 'MS_LS' and current_speed == 'HS': continue
            
            # Правило 3: Перегрузка (Flow Control)
            if cons_complex >= 2:
                # Требуем простую разворотную фигуру, чтобы сбросить напряжение
                if not f["is_turn"] or f["is_complex"]: continue

            # Правило 4: Контроль оси Y
            if current_axis == "Y" and figures_on_y >= 1 and not f["changes_axis"]: continue 
            if current_axis == "X" and f["changes_axis"] and i >= length - 2: continue 

            valid_figs.append(f)

        # Failsafe: если фильтры оказались слишком жесткими, ослабляем Flow Control
        if not valid_figs:
            valid_figs = [f for f in clean_pool if (f["req_entry"] in ['Any', current_att]) and (f["req_speed"] != 'LS' or current_speed == 'LS')]

        if not valid_figs: break # Совсем тупик (база слишком мала)

        fig = random.choice(valid_figs)

        sequence.append({
            "macro": fig["macro"],
            "aresti": ", ".join(fig["aresti"]),
            "speed_in": current_speed,
            "att_in": current_att,
            "axis": current_axis,
            "is_complex": fig["is_complex"]
        })

        # --- ОБНОВЛЕНИЕ ТЕЛЕМЕТРИИ ДЛЯ СЛЕДУЮЩЕЙ ФИГУРЫ ---
        if fig["net_flip"]: current_att = "I" if current_att == "U" else "U"
        current_speed = fig["out_speed"]
        if fig["changes_axis"]: current_axis = "Y" if current_axis == "X" else "X"
        if current_axis == "Y": figures_on_y += 1
        else: figures_on_y = 0
        cons_complex = cons_complex + 1 if fig["is_complex"] else 0

    return sequence

# --- Streamlit UI ---
st.set_page_config(page_title="Unlimited Simulator", page_icon="✈️")
st.title("🏆 Unlimited Simulator (Physics Engine)")
st.write("Движок трекает Upright/Inverted полет, строго требует сваливание (LS) для штопоров и разбавляет сложные связки простыми разворотами.")

num_figs = st.sidebar.slider("Количество фигур", 5, 15, 10)

if st.button("Сгенерировать комплекс"):
    complex_data = build_aerodynamic_data_sequence(num_figs)
    final_string = " ".join([fig["macro"] for fig in complex_data])
    
    st.success("✅ Готово! Копируй в OpenAero и нажимай **Separate figures**.")
    st.code(final_string, language="text")
    
    st.write("### Телеметрия полета:")
    for i, fig in enumerate(complex_data):
        att_icon = "⬆️ Пузо" if fig["att_in"] == "U" else "⬇️ Спина"
        spd_icon = "🔥 HS" if fig["speed_in"] == "HS" else ("💨 MS" if fig["speed_in"] == "MS" else "🛑 LS (Stall)")
        cplx_icon = "⚠️ Сложная" if fig["is_complex"] else "✅ Простая"
        st.write(f"**{i+1}.** `{fig['macro']}`")
        st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;*Вход:* {att_icon} | {spd_icon} | {cplx_icon}")
