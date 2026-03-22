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
# 1. АБСОЛЮТНАЯ МАТРИЦА АРЕСТИ (ARESTI PHYSICS V2)
# ==========================================
def does_figure_change_axis(aresti_list):
    changes = False
    for code in aresti_list:
        parts = code.split('.')
        if len(parts) == 4:
            family, sub, row, col = map(int, parts)
            # 1. Виражи (Сем 2): 90° (ряд 1) и 270° (ряд 3)
            if family == 2 and row in [1, 3]: changes = not changes 
            # 2. Вращения (Сем 9): 1/4 и 3/4 бочки (колонки 1, 3, 5, 7)
            elif family == 9 and col % 2 != 0:
                # Только на строго вертикальных линиях (ряды 3 и 5) или в штопоре (подгруппы 11, 12)
                if row in [3, 5] or sub >= 11: changes = not changes
    return changes

def analyze_figure(f_data):
    aresti_list = f_data["aresti"]
    macro = f_data["macro"]
    base = aresti_list[0]
    parts = base.split('.')
    family, sub, row, col = map(int, parts) if len(parts) == 4 else (0, 0, 0, 0)

    roll_codes = aresti_list[1:]
    has_spin = any(r.split('.')[1] >= '11' for r in roll_codes if len(r.split('.')) == 4)
    has_flick = any(r.split('.')[1] in ['9', '10'] for r in roll_codes if len(r.split('.')) == 4)

    # --- 1. ТРЕКИНГ ПЕРЕВОРОТОВ (БЕЗ ИСКАЖЕНИЯ МАКРОСА) ---
    # Опрокидывают ли самолет базовые фигуры? (Кубанки и Хумпти НЕ опрокидывают!)
    base_flip = False
    if family == 6 and sub == 2: base_flip = True # Колокол (колесами вверх)
    elif family == 7 and sub in [1, 2]: base_flip = True # Полупетли
    
    # Считаем только полубочки и 1.5 бочки (колонки 2 и 6)
    roll_flips = sum(1 for c in roll_codes if len(c.split('.')) == 4 and c.split('.')[3] in ['2', '6'])
    net_flip = base_flip ^ (roll_flips % 2 != 0)
    
    # Нативное положение входа (колонки 1,3 = Прямо; 2,4 = Спина)
    native_entry = 'U' if col in [1, 3] else 'I'
    
    # Читаем явные плюсы/минусы судей из макроса, если их нет - берем нативное
    m_clean = re.sub(r'[^a-zA-Z0-9\+\-]', '', macro)
    req_entry = 'I' if m_clean.startswith('-') else ('U' if m_clean.startswith('+') else native_entry)
    
    # Считаем математический выход
    calc_exit = 'I' if (req_entry == 'U' and net_flip) or (req_entry == 'I' and not net_flip) else 'U'
    exit_att = 'I' if m_clean.endswith('-') else ('U' if m_clean.endswith('+') else calc_exit)

    # --- 2. ИДЕАЛЬНАЯ МАТРИЦА СКОРОСТЕЙ ---
    starts_up = False; starts_down = False
    exits_up = False; exits_down = False

    if family == 1 and sub >= 2:
        # Линии: нечетные ряды идут вверх, четные - вниз
        if row % 2 != 0: starts_up = True
        else: starts_down = True
        # Выходы для линий (по каталогу Арести)
        if row in [1, 4, 6, 8]: exits_up = True
        elif row in [2, 3, 5, 7]: exits_down = True
    elif family in [5, 6]: 
        starts_up = True; exits_down = True
    elif family in [7, 8]:
        # Петли и Комбинации: Колонки 1,2 = старт СНИЗУ (идем ВВЕРХ). Колонки 3,4 = старт СВЕРХУ (идем ВНИЗ)
        if col in [1, 2]: starts_up = True
        elif col in [3, 4]: starts_down = True
        
        if family == 7 and sub in [1, 2, 3]: # Полупетли и 3/4 петли
            if starts_up: exits_up = True
            elif starts_down: exits_down = True
        elif family == 8 and sub != 8: # Хумпти и Кубанки (кроме двойных) возвращают обратно
            if starts_up: exits_down = True
            elif starts_down: exits_up = True

    # Трансляция в скорости энергии
    if starts_up: req_speed = 'HS_REQ'
    elif starts_down: req_speed = 'LS_REQ'
    else: req_speed = 'MS_REQ'

    if exits_up: out_speed = 'LS'
    elif exits_down: out_speed = 'HS'
    else: out_speed = 'MS'

    if has_spin: req_speed = 'LS_REQ'
    elif has_flick and req_speed == 'HS_REQ': req_speed = 'MS_REQ' 

    return {
        "family": family, "base_code": base, "roll_codes": roll_codes,
        "req_speed": req_speed, "out_speed": out_speed, 
        "req_entry": req_entry, "exit_att": exit_att, 
        "changes_axis": does_figure_change_axis(aresti_list),
        "has_flick": has_flick, "k_factor": f_data.get("k_factor", 15)
    }

# ==========================================
# 2. АППАРАТНЫЕ ПАРАШЮТЫ С ОСЕЙ
# ==========================================
def get_y_recovery_figure(att, speed):
    if speed == 'HS': return {"macro": "-h4-" if att == 'I' else "+h4+", "aresti": ["5.2.1.2", "9.1.5.1"], "req_speed": "HS_REQ", "out_speed": "HS", "exit_att": att, "axis": "Y", "changes_axis": True, "k_factor": 25, "has_flick": False}
    elif speed == 'LS': return {"macro": "-iv4-" if att == 'I' else "+iv4+", "aresti": ["1.1.6.3", "9.1.5.1"], "req_speed": "LS_REQ", "out_speed": "HS", "exit_att": att, "axis": "Y", "changes_axis": True, "k_factor": 15, "has_flick": False}
    else: return {"macro": "-1j-" if att == 'I' else "+1j+", "aresti": ["2.1.1.1"], "req_speed": "MS_REQ", "out_speed": "MS", "exit_att": att, "axis": "Y", "changes_axis": True, "k_factor": 10, "has_flick": False}

def get_x_recovery_figure(att, speed):
    if speed == 'HS': return {"macro": "-o-" if att == 'I' else "+o+", "aresti": ["7.4.1.1"], "req_speed": "HS_REQ", "out_speed": "HS", "exit_att": att, "axis": "X", "changes_axis": False, "k_factor": 12, "has_flick": False}
    elif speed == 'LS': return {"macro": "-a+" if att == 'I' else "+2a+", "aresti": ["7.2.3.3"], "req_speed": "LS_REQ", "out_speed": "HS", "exit_att": "U", "axis": "X", "changes_axis": False, "k_factor": 15, "has_flick": False}
    else: return {"macro": "-j-" if att == 'I' else "+j+", "aresti": ["2.2.1.1"], "req_speed": "MS_REQ", "out_speed": "MS", "exit_att": att, "axis": "X", "changes_axis": False, "k_factor": 10, "has_flick": False}

# ==========================================
# 3. ГЕНЕРАТОР КОМПЛЕКСОВ
# ==========================================
DATABASE = load_database()

def build_tournament_sequence(num_hard, num_link, max_k_total, link_threshold):
    length = num_hard + num_link
    sequence = []
    current_att = "U"     
    current_speed = "MS"  
    current_axis = "X"    
    
    current_k = 0
    hard_count = 0
    link_count = 0
    cons_hard = 0
    figures_since_y = 99  
    used_bases = set()
    used_rolls = set()

    if not DATABASE:
        st.error("В базе нет валидных фигур!")
        return []

    for i in range(length):
        # 1. Защита оси Y
        if current_axis == "Y":
            fig = get_y_recovery_figure(current_att, current_speed)
            sequence.append({
                "macro": fig["macro"], "speed_in": current_speed, "att_in": current_att, 
                "att_out": fig["exit_att"], "req_speed": fig["req_speed"], "axis": "Y", "k_factor": fig["k_factor"]
            })
            current_att, current_speed, current_axis = fig["exit_att"], fig["out_speed"], "X"
            figures_since_y = 0
            current_k += fig["k_factor"]; link_count += 1; cons_hard = 0
            continue

        valid_figs = []
        for family, figs in DATABASE.items():
            for f in figs:
                physics = analyze_figure(f)
                
                # Фильтр положений
                if physics["req_entry"] != current_att: continue
                # Запрет штопорных бочек на перегрузке
                if current_speed == 'HS' and physics.get("has_flick"): continue
                
                # ИДЕАЛЬНАЯ СТЫКОВКА СКОРОСТЕЙ
                req = physics["req_speed"]
                match_speed = False
                if current_speed == 'HS' and req == 'HS_REQ': match_speed = True
                elif current_speed == 'LS' and req == 'LS_REQ': match_speed = True
                elif current_speed == 'MS' and req in ['LS_REQ', 'MS_REQ']: match_speed = True
                
                # Легитимность осей
                if match_speed and not (physics["changes_axis"] and physics["family"] not in [2, 9]):
                    fig_copy = f.copy()
                    fig_copy.update(physics)
                    valid_figs.append(fig_copy)

        if figures_since_y < 2 or i >= length - 2:
            valid_figs = [f for f in valid_figs if not f.get("changes_axis")]

        hard_figs = [f for f in valid_figs if f.get("k_factor", 15) > link_threshold]
        link_figs = [f for f in valid_figs if f.get("k_factor", 15) <= link_threshold]
        
        force_link = False; force_hard = False
        if cons_hard >= 3: force_link = True
        elif hard_count >= num_hard: force_link = True
        elif link_count >= num_link: force_hard = True
        
        figs_left = length - i
        if figs_left > 0 and ((max_k_total - current_k) / figs_left) < link_threshold:
            force_link = True
            
        pool_to_use = valid_figs
        if force_link and link_figs: pool_to_use = link_figs
        elif force_hard and hard_figs: pool_to_use = hard_figs
        elif hard_figs and link_figs:
            pool_to_use = hard_figs if random.random() < 0.75 else link_figs

        strict_figs = [f for f in pool_to_use if f.get("base_code") not in used_bases and not any(r in f.get("roll_codes", []) for r in used_rolls)]

        if strict_figs: fig = random.choice(strict_figs)
        elif pool_to_use: fig = random.choice(pool_to_use)
        else:
            fig = get_x_recovery_figure(current_att, current_speed)
            fig["base_code"] = "X_REC"
            fig["roll_codes"] = []

        # МАКРОС ИДЕТ КАК ЕСТЬ!
        sequence.append({
            "macro": fig["macro"], "speed_in": current_speed, "att_in": current_att, 
            "att_out": fig["exit_att"], "req_speed": fig.get("req_speed", ""), "axis": "X", "k_factor": fig.get("k_factor", 15)
        })

        if "base_code" in fig and fig["base_code"] != "X_REC":
            used_bases.add(fig["base_code"])
            used_rolls.update(fig.get("roll_codes", []))

        current_att = fig["exit_att"] 
        current_speed = fig["out_speed"]
        current_k += fig.get("k_factor", 15)
        
        if fig.get("k_factor", 15) > link_threshold:
            hard_count += 1; cons_hard += 1
        else:
            link_count += 1; cons_hard = 0
            
        if fig.get("changes_axis"):
            current_axis = "Y"; figures_since_y = 0
        else:
            figures_since_y += 1

    return sequence, current_k

# --- Streamlit UI ---
st.set_page_config(page_title="Unlimited World Champ", page_icon="🏆", layout="wide")
st.title("🏆 Unlimited Pro (Aresti Matrix v2)")
st.write("Скрипт читает физику строго по каталогу Арести. Макросы передаются OpenAero в первозданном виде. 100% стыковка гарантирована.")

st.sidebar.header("🛠 Бюджет CIVA")
num_hard = st.sidebar.slider("Боевые фигуры (Сложные)", 5, 12, 10)
num_link = st.sidebar.slider("Связочные фигуры (Простые)", 2, 6, 4)
max_k_total = st.sidebar.slider("Лимит сложности (Max Total K)", 300, 500, 420)
link_threshold = st.sidebar.slider("Порог K-фактора (Связочная <= K)", 10, 35, 25)

if st.button("Сгенерировать комплекс"):
    complex_data, total_k = build_tournament_sequence(num_hard, num_link, max_k_total, link_threshold)
    final_string = " ".join([fig["macro"] for fig in complex_data])
    
    st.success(f"✅ Готово! Итоговый K-Фактор: **{total_k}K**")
    st.code(final_string, language="text")
    
    st.write("### Телеметрия:")
    for i, fig in enumerate(complex_data):
        att_in = "⬆️ Прямо" if fig["att_in"] == "U" else "⬇️ Спина"
        spd_icon = "🛑 Stall (LS)" if fig["speed_in"] == "LS" else ("🔥 Fast (HS)" if fig["speed_in"] == "HS" else "💨 Cruise (MS)")
        req_icon = "⬇️ Разгон (LS_REQ)" if fig.get("req_speed") == "LS_REQ" else ("⬆️ Энергия (HS_REQ)" if fig.get("req_speed") == "HS_REQ" else "➡️ Горизонт (MS_REQ)")
        type_icon = "⚔️ **Боевая**" if fig["k_factor"] > link_threshold else "🔗 *Связочная*"
        
        st.write(f"**{i+1}.** `{fig['macro']}` | **[{fig['k_factor']}K]** {type_icon}")
        st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;Вход: {att_in} ({spd_icon}) ➡️ Фигура просит: {req_icon} | Ось: {fig.get('axis', 'X')}")
