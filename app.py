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
# 1. АЭРОДИНАМИЧЕСКИЙ ДВИЖОК (ЧТЕНИЕ АРЕСТИ)
# ==========================================
def analyze_figure_physics(aresti_list):
    if not aresti_list: return None
    base = aresti_list[0]
    parts = base.split('.')
    if len(parts) < 4: return None
    
    family = int(parts[0])
    sub = int(parts[1])
    row = int(parts[2])
    col = int(parts[3])

    # 1. ПОЛОЖЕНИЕ НА ВХОДЕ (Upright / Inverted)
    # По правилам каталога Арести, 1 и 3 столбцы начинаются из прямого полета, 2 и 4 - со спины.
    if family == 7 and sub == 2 and row in [3, 4]: # Исключение: Нисходящие полупетли (Split-S)
        req_entry = 'U' if col in [1, 4] else 'I'
    elif family == 1 and sub == 1 and row == 1: # Исключение: Горизонтальные пролеты
        req_entry = 'U' if col in [1, 3] else 'I'
    else:
        req_entry = 'U' if col in [1, 3] else 'I'

    # 2. БАЗОВЫЙ ПЕРЕВОРОТ (Меняет ли сама фигура положение без бочек?)
    base_flip = False
    if family == 7 and sub == 2: base_flip = True # Полупетли (Иммельман, Сплит)
    if family == 8 and sub == 5: base_flip = True # Полукубинцы

    # 3. ВРАЩЕНИЯ И ШТОПОРЫ
    roll_flips = 0
    has_spin = False
    changes_axis = False

    for code in aresti_list[1:]:
        rp = code.split('.')
        if len(rp) == 4 and rp[0] == '9':
            if rp[1] in ['11', '12', '13']: has_spin = True
            
            b_line = int(rp[2])
            c_rot = int(rp[3])
            
            # Универсальное правило: 1/2 (2) и 1.5 (6) бочки на ЛЮБОЙ линии меняют положение самолета!
            if c_rot in [2, 6]:
                roll_flips += 1
                
            # 1/4 (1) и 3/4 (3) бочки на вертикалях меняют ось (X <-> Y)
            if b_line in [3, 5] and c_rot % 2 != 0:
                changes_axis = not changes_axis

    # Итоговое изменение положения (XOR базовой фигуры и бочек)
    net_flip = base_flip ^ (roll_flips % 2 != 0)

    # 4. УПРАВЛЕНИЕ ЭНЕРГИЕЙ (Скорость на выходе)
    out_speed = 'HS' # По умолчанию скорость большая
    # Фигуры, которые выходят из вертикали/45 ВВЕРХ в горизонт, гасят скорость до минимальной (LS)
    if family == 1 and sub == 1 and row == 6: out_speed = 'LS' 
    if family == 1 and sub == 2 and row in [1, 2, 3, 4]: out_speed = 'LS'
    if family == 7 and sub == 2 and row in [1, 2]: out_speed = 'LS' # Иммельманы
    if family == 8 and sub == 6 and row in [1, 2, 3, 4]: out_speed = 'LS' # Reverse P-Loops
    
    if family == 2 or (family == 1 and sub == 1 and row == 1): out_speed = 'MS' # Виражи и прямые

    # Требования к скорости на входе
    req_speed = 'Any'
    if has_spin: req_speed = 'LS' # Штопор ТОЛЬКО на сваливании
    elif family == 2 or (family == 1 and sub == 1 and row == 1): req_speed = 'MS_LS' # Плоские запрещены на HS
    elif family == 7 and sub == 2 and row in [3, 4]: req_speed = 'MS_LS' # Сплит-С запрещен на HS

    # 5. СЛОЖНОСТЬ (Flow Control)
    is_complex = len(aresti_list) >= 3
    # Фигуры, разворачивающие полет на 180 градусов
    is_turn = family in [5, 6, 8] or (family == 2 and sub == 2) or (family == 7 and sub == 2)

    return {
        "req_entry": req_entry, "net_flip": net_flip, 
        "out_speed": out_speed, "req_speed": req_speed,
        "is_complex": is_complex, "is_turn": is_turn,
        "changes_axis": changes_axis, "has_spin": has_spin
    }

# Санитарный фильтр (защита от мусора из парсера)
def is_clean_macro(macro, aresti_list):
    m = macro.lower()
    if any(w in m for w in ["sequence", "generated", "unknown", "training", "unlimited", "free", "known"]): return False
    if not aresti_list or len(aresti_list[0].split('.')) < 4: return False
    return True

# ==========================================
# 2. ГЕНЕРАТОР КОМПЛЕКСОВ
# ==========================================
DATABASE = load_database()

def build_tournament_sequence(length):
    sequence = []
    
    current_att = "U"     # Начинаем пузом вниз
    current_speed = "MS"  # Стартовая скорость средняя
    current_axis = "X"    # Главная ось
    
    figures_on_y = 0
    cons_complex = 0      # Счетчик сложных фигур подряд

    # 1. Готовим базу
    clean_pool = []
    for family, figs in DATABASE.items():
        for f in figs:
            if is_clean_macro(f["macro"], f["aresti"]):
                physics = analyze_figure_physics(f["aresti"])
                if physics:
                    f.update(physics)
                    clean_pool.append(f)

    if not clean_pool:
        st.error("В базе не осталось валидных фигур! Проверьте civa_database.json")
        return []

    # 2. Интеллектуальная сборка
    for i in range(length):
        valid_figs = []
        for f in clean_pool:
            # Правило 1: Строгий трекинг положения самолета!
            if f["req_entry"] != 'Any' and f["req_entry"] != current_att: continue
            
            # Правило 2: Скорость (Штопор только на LS, запрет плоских на HS)
            if f["req_speed"] == 'LS' and current_speed != 'LS': continue
            if f["req_speed"] == 'MS_LS' and current_speed == 'HS': continue
            
            # Правило 3: Защита пилота от перегрузки
            if cons_complex >= 2:
                # Требуем ПРОСТУЮ фигуру, которая разворачивает самолет
                if not f["is_turn"] or f["is_complex"]: continue

            # Правило 4: Защита поперечной оси
            if current_axis == "Y" and figures_on_y >= 1 and not f["changes_axis"]: continue 
            if current_axis == "X" and f["changes_axis"] and i >= length - 2: continue 

            valid_figs.append(f)

        # Failsafe: если фильтры слишком жесткие, ослабляем Flow Control
        if not valid_figs:
            valid_figs = [f for f in clean_pool if f["req_entry"] == current_att and (f["req_speed"] != 'LS' or current_speed == 'LS')]

        if not valid_figs: 
            st.warning(f"Сборка остановлена на фигуре {i+1}: в базе нет подходящего маневра для текущего состояния (Положение: {current_att}, Скорость: {current_speed}).")
            break

        fig = random.choice(valid_figs)

        sequence.append({
            "macro": fig["macro"],
            "aresti": ", ".join(fig["aresti"]),
            "speed_in": current_speed,
            "att_in": current_att,
            "axis": current_axis,
            "is_complex": fig["is_complex"],
            "has_spin": fig["has_spin"]
        })

        # --- ТЕЛЕМЕТРИЯ (Обновляем состояние самолета для следующей фигуры) ---
        if fig["net_flip"]: current_att = "I" if current_att == "U" else "U"
        current_speed = fig["out_speed"]
        
        if fig["changes_axis"]: current_axis = "Y" if current_axis == "X" else "X"
        if current_axis == "Y": figures_on_y += 1
        else: figures_on_y = 0
        
        cons_complex = cons_complex + 1 if fig["is_complex"] else 0

    return sequence

# --- Streamlit UI ---
st.set_page_config(page_title="Unlimited Simulator", page_icon="✈️")
st.title("🏆 Unlimited Pro (Physics Engine)")
st.write("Идеальный трекинг перевернутого полета. Штопоры ставятся **только** на скорости сваливания (LS).")

num_figs = st.sidebar.slider("Количество фигур", 5, 15, 10)

if st.button("Сгенерировать комплекс"):
    complex_data = build_tournament_sequence(num_figs)
    final_string = " ".join([fig["macro"] for fig in complex_data])
    
    st.success("✅ Готово! Копируй в OpenAero и нажимай **Separate figures**.")
    st.code(final_string, language="text")
    
    st.write("### Телеметрия полета:")
    for i, fig in enumerate(complex_data):
        att_icon = "⬆️ Прямой" if fig["att_in"] == "U" else "⬇️ На спине"
        spd_icon = "🛑 Сваливание (LS)" if fig["speed_in"] == "LS" else ("🔥 Пикирование (HS)" if fig["speed_in"] == "HS" else "💨 Средняя (MS)")
        cplx_icon = "⚠️ Сложная" if fig["is_complex"] else "✅ Простая"
        spin_txt = "🌀 **ШТОПОР!**" if fig["has_spin"] else ""
        
        st.write(f"**{i+1}.** `{fig['macro']}` {spin_txt}")
        st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;*Вход:* {att_icon} | {spd_icon} | {cplx_icon}")
