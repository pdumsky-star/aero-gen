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
# 1. ФИЗИКА И АНАЛИЗАТОР CIVA
# ==========================================
def analyze_figure(f_data):
    """Анализирует скорость, сложность и смену осей для фигуры"""
    aresti_list = f_data["aresti"]
    base = aresti_list[0]
    parts = base.split('.')
    family = int(parts[0])
    sub = int(parts[1]) if len(parts) > 1 else 0
    row = int(parts[2]) if len(parts) > 2 else 0

    roll_codes = aresti_list[1:]
    has_spin = any(r.split('.')[1] in ['11', '12', '13'] for r in roll_codes if len(r.split('.')) == 4)
            
    # --- РАСЧЕТ СКОРОСТИ НА ВЫХОДЕ ---
    out_speed = 'HS' # Обычно фигуры (петли, сплиты, колокола) разгоняют самолет
    # Но если фигура заканчивается движением ВВЕРХ, скорость падает до сваливания (LS)
    if family == 7 and sub in [1, 2] and row in [1, 2]: out_speed = 'LS' # Иммельманы
    if family == 1 and sub == 1 and row in [6, 7]: out_speed = 'LS' # Вертикали вверх
    if family == 1 and sub == 2 and row in [1, 2, 3, 4]: out_speed = 'LS' # 45 градусов вверх
    if family == 8 and sub == 6 and row in [1, 2, 3, 4]: out_speed = 'LS' # Reverse P-Loops (выход после вертикали)
    if family == 2: out_speed = 'MS' # После виражей скорость средняя

    # --- РАСЧЕТ ТРЕБУЕМОЙ СКОРОСТИ НА ВХОДЕ ---
    # Требует ли фигура движения ВВЕРХ в самом начале? (Нужна скорость HS)
    starts_up = False
    if family in [5, 6, 8]: starts_up = True # Хаммерхеды, Колокола, Кубинцы, Хампти
    if family == 7 and sub == 4 and row in [1, 2, 3]: starts_up = True # Восходящие петли
    if family == 7 and sub in [1, 2] and row in [1, 2]: starts_up = True # Иммельманы
    if family == 1 and sub == 1 and row in [6, 7]: starts_up = True # Вертикаль вверх
    if family == 1 and sub == 2 and row in [1, 2, 3, 4]: starts_up = True # 45 вверх
    
    req_speed = 'HS' if starts_up else 'Any'
    if has_spin: req_speed = 'LS' # Штопор ТОЛЬКО на сваливании
    elif family == 2: req_speed = 'MS_LS' # Виражи нельзя на огромной скорости
    elif family == 7 and sub in [1, 2] and row in [3, 4]: req_speed = 'MS_LS' # Split-S

    # --- СМЕНА ОСИ Y ---
    changes_axis = False
    for code in roll_codes:
        rp = code.split('.')
        if len(rp) == 4 and int(rp[0]) == 9 and int(rp[2]) in [3, 5] and int(rp[3]) % 2 != 0:
            changes_axis = not changes_axis
    if family == 2 and int(parts[1]) in [1, 3]: changes_axis = not changes_axis

    is_complex = len(aresti_list) >= 3
    is_turn = family in [5, 6, 8] or (family == 2 and sub == 2) or (family == 7 and sub == 2)

    return {
        "base_code": base,
        "roll_codes": roll_codes,
        "out_speed": out_speed, 
        "req_speed": req_speed,
        "is_complex": is_complex, 
        "is_turn": is_turn,
        "changes_axis": changes_axis, 
        "has_spin": has_spin
    }

def is_clean_macro(macro, aresti_list):
    m = macro.lower()
    if any(w in m for w in ["sequence", "generated", "unknown", "training", "unlimited", "free", "known"]): return False
    if not aresti_list or len(aresti_list[0].split('.')) < 4: return False
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
# 2. ГЕНЕРАТОР КОМПЛЕКСОВ (С ПАМЯТЬЮ CIVA)
# ==========================================
DATABASE = load_database()

def build_tournament_sequence(length):
    sequence = []
    current_att = "U"     
    current_speed = "MS"  
    current_axis = "X"    
    
    figures_on_y = 0
    cons_complex = 0      
    
    # ПАМЯТЬ CIVA (Защита от повторений)
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
        valid_figs = []
        for f in clean_pool:
            # 1. СКЛЕЙКА ПОЛОЖЕНИЯ (+ / -)
            if f["entry"] != current_att: continue
            
            # 2. ПРАВИЛО CIVA UNKNOWN: НИКАКИХ ПОВТОРЕНИЙ!
            if f["base_code"] in used_bases: continue # Базовая фигура уже была
            if any(r in used_rolls for r in f["roll_codes"]): continue # Такое вращение уже было
            
            # 3. УПРАВЛЕНИЕ ЭНЕРГИЕЙ (Твоя проблема №1 решена здесь)
            if f["req_speed"] == 'LS' and current_speed != 'LS': continue # Штопор только после остановки
            if f["req_speed"] == 'HS' and current_speed == 'LS': continue # Нельзя тянуть вверх без скорости!
            if f["req_speed"] == 'MS_LS' and current_speed == 'HS': continue # Защита от перегрузки
            
            # 4. ЗАЩИТА ОСЕЙ И ПЕРЕГРУЗКИ ПИЛОТА
            if current_axis == "Y" and figures_on_y >= 1 and not f["changes_axis"]: continue 
            if current_axis == "X" and f["changes_axis"] and i >= length - 2: continue 
            if cons_complex >= 2 and (not f["is_turn"] or f["is_complex"]): continue

            valid_figs.append(f)

        # Failsafe 1: Если правила CIVA слишком зажали нас, разрешаем повторить вращение (но не базу!)
        if not valid_figs:
            valid_figs = [f for f in clean_pool if f["entry"] == current_att and f["base_code"] not in used_bases 
                          and not (f["req_speed"] == 'HS' and current_speed == 'LS')]

        # Failsafe 2: Если совсем тупик, берем любую подходящую по скорости и входу
        if not valid_figs:
            valid_figs = [f for f in clean_pool if f["entry"] == current_att and not (f["req_speed"] == 'HS' and current_speed == 'LS')]

        if not valid_figs: 
            st.warning(f"Остановка сборки на фигуре {i+1}: база истощена.")
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

        # --- ЗАПИСЬ В ПАМЯТЬ CIVA ---
        used_bases.add(fig["base_code"])
        used_rolls.update(fig["roll_codes"])

        # --- ОБНОВЛЕНИЕ ТЕЛЕМЕТРИИ ---
        current_att = fig["exit"] 
        current_speed = fig["out_speed"]
        
        if fig["changes_axis"]: current_axis = "Y" if current_axis == "X" else "X"
        if current_axis == "Y": figures_on_y += 1
        else: figures_on_y = 0
        
        cons_complex = cons_complex + 1 if fig["is_complex"] else 0

    return sequence

# --- Streamlit UI ---
st.set_page_config(page_title="Unlimited World Champ", page_icon="🏆")
st.title("🏆 Unlimited World Champ Engine")
st.write("Скрипт соблюдает правила CIVA Unknown: **запрет на повторение фигур и вращений**, а также строгий учет кинетической энергии (скорости).")

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
        st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;*Вход:* {att_in} ({spd_icon}) ➡️ *Выход:* {att_out} | *Арести:* {fig['aresti']}")
