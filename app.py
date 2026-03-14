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
# 1. АБСОЛЮТНЫЙ АНАЛИЗАТОР АРЕСТИ (БЕЗ ТЕКСТА)
# ==========================================
def does_figure_change_axis(aresti_list):
    changes = False
    for code in aresti_list:
        parts = code.split('.')
        if len(parts) == 4:
            family, sub, row, col = map(int, parts)
            # Виражи (Fam 2): Ряды 1 (90°) и 3 (270°) меняют ось
            if family == 2 and row in [1, 3]: changes = not changes 
            # Вращения (Fam 9): 1/4 и 3/4 вращения на вертикалях меняют ось
            elif family == 9 and col % 2 != 0:
                if sub <= 10 and row in [3, 5]: changes = not changes
                elif sub in [11, 12, 13] and row == 1: changes = not changes
    return changes

def analyze_figure(f_data, current_att):
    aresti_list = f_data["aresti"]
    base = aresti_list[0]
    parts = base.split('.')
    family, sub, row, col = map(int, parts) if len(parts) == 4 else (0, 0, 0, 0)

    roll_codes = aresti_list[1:]
    has_spin = any(r.split('.')[1] in ['11', '12', '13'] for r in roll_codes if len(r.split('.')) == 4)
    has_flick = any(r.split('.')[1] in ['9', '10'] for r in roll_codes if len(r.split('.')) == 4)

    # --- 1. ВЫЧИСЛЕНИЕ ПЕРЕВОРОТА СТРОГО ПО АРЕСТИ ---
    base_flip = False
    # Петли и восьмерки (Fam 7 и 8) опрокидывают самолет
    if family == 7 and sub in [1, 2, 3]: base_flip = True
    if family == 8 and sub in [1, 2, 3, 4, 5, 6, 7, 8]: base_flip = True
    # Колокола и скольжения (Fam 6) всегда меняют положение
    if family == 6: base_flip = True 
    
    # Считаем только полубочки (колонки 2) и 1.5 бочки (колонки 6)
    roll_flips = sum(1 for c in roll_codes if len(c.split('.')) == 4 and c.split('.')[3] in ['2', '6'])
    net_flip = base_flip ^ (roll_flips % 2 != 0)
    
    # Вычисляем, в каком положении мы окажемся на выходе
    exit_att = 'I' if (current_att == 'U' and net_flip) or (current_att == 'I' and not net_flip) else 'U'

    # --- 2. ЖЕЛЕЗОБЕТОННАЯ МАТРИЦА НАПРАВЛЕНИЙ И СКОРОСТЕЙ ---
    starts_dir = 'HORIZ'
    ends_dir = 'HORIZ'

    if family == 1: # Линии и углы
        if sub == 1: starts_dir = 'HORIZ'; ends_dir = 'HORIZ'
        elif sub in [2, 3]: # 45 и 90 градусов
            if row <= 4: starts_dir = 'UP'; ends_dir = 'UP'
            else: starts_dir = 'DOWN'; ends_dir = 'DOWN'
    elif family in [5, 6]: # Хаммерхеды и Колокола
        starts_dir = 'UP'; ends_dir = 'DOWN'
    elif family == 7: # Петли
        starts_dir = 'HORIZ'; ends_dir = 'HORIZ' 
    elif family == 8: # Комбинации
        if sub <= 4: starts_dir = 'UP'; ends_dir = 'DOWN' # Хумпти-Бампы
        elif sub in [5, 6]: starts_dir = 'UP'; ends_dir = 'DOWN' # Кубинские восьмерки
        elif sub in [7, 8]: starts_dir = 'HORIZ'; ends_dir = 'HORIZ' # Обратные кубинские

    if has_spin: starts_dir = 'SPIN'

    # Присваиваем скорости на основе физических направлений!
    if starts_dir == 'UP': req_speed = 'HS_REQ'
    elif starts_dir in ['DOWN', 'SPIN']: req_speed = 'LS_REQ'
    else: req_speed = 'MS_REQ'

    if ends_dir == 'UP': out_speed = 'LS'
    elif ends_dir == 'DOWN': out_speed = 'HS'
    else: out_speed = 'MS'

    return {
        "family": family, "base_code": base, "roll_codes": roll_codes,
        "starts_dir": starts_dir, "req_speed": req_speed, "out_speed": out_speed, 
        "exit_att": exit_att, "is_complex": len(aresti_list) >= 3, 
        "changes_axis": does_figure_change_axis(aresti_list),
        "has_spin": has_spin, "has_flick": has_flick, "k_factor": f_data.get("k_factor", 15)
    }

def wrap_macro(macro, att_in, att_out):
    """АГРЕССИВНЫЙ ВРАППЕР: Срезает мусор и жестко кует положения"""
    m_body = re.sub(r'^[\+\-]+|[\+\-]+$', '', macro)
    sign_in = '+' if att_in == 'U' else '-'
    sign_out = '+' if att_out == 'U' else '-'
    return f"{sign_in}{m_body}{sign_out}"

# ==========================================
# 2. АППАРАТНЫЕ ПАРАШЮТЫ С ОСЕЙ
# ==========================================
def get_y_recovery_figure(att, speed):
    if speed == 'HS': return {"macro": "h4", "aresti": ["5.2.1.2", "9.1.5.1"], "req_speed": "HS_REQ", "out_speed": "HS", "exit_att": att, "axis": "Y", "changes_axis": True, "k_factor": 25, "has_flick": False}
    elif speed == 'LS': return {"macro": "iv4", "aresti": ["1.1.6.3", "9.1.5.1"], "req_speed": "LS_REQ", "out_speed": "HS", "exit_att": att, "axis": "Y", "changes_axis": True, "k_factor": 15, "has_flick": False}
    else: return {"macro": "1j", "aresti": ["2.1.1.1"], "req_speed": "MS_REQ", "out_speed": "MS", "exit_att": att, "axis": "Y", "changes_axis": True, "k_factor": 10, "has_flick": False}

def get_x_recovery_figure(att, speed):
    if speed == 'HS': return {"macro": "o", "aresti": ["7.4.1.1"], "req_speed": "HS_REQ", "out_speed": "HS", "exit_att": att, "axis": "X", "changes_axis": False, "k_factor": 12, "has_flick": False}
    elif speed == 'LS': return {"macro": "a", "aresti": ["7.2.3.3"], "req_speed": "LS_REQ", "out_speed": "HS", "exit_att": "U", "axis": "X", "changes_axis": False, "k_factor": 15, "has_flick": False}
    else: return {"macro": "j", "aresti": ["2.2.1.1"], "req_speed": "MS_REQ", "out_speed": "MS", "exit_att": att, "axis": "X", "changes_axis": False, "k_factor": 10, "has_flick": False}

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
        if current_axis == "Y":
            fig = get_y_recovery_figure(current_att, current_speed)
            final_macro = wrap_macro(fig["macro"], current_att, fig["exit_att"])
            sequence.append({
                "macro": final_macro, "speed_in": current_speed, "att_in": current_att, 
                "att_out": fig["exit_att"], "req_speed": fig["req_speed"], "axis": "Y", "k_factor": fig["k_factor"]
            })
            current_att, current_speed, current_axis = fig["exit_att"], fig["out_speed"], "X"
            figures_since_y = 0
            current_k += fig["k_factor"]; link_count += 1; cons_hard = 0
            continue

        valid_figs = []
        for family, figs in DATABASE.items():
            for f in figs:
                physics = analyze_figure(f, current_att)
                
                # Запрет штопорных бочек на огромной скорости
                if current_speed == 'HS' and physics.get("has_flick"): continue
                
                # СТРОЖАЙШИЙ КОНТРОЛЬ СКОРОСТЕЙ
                req = physics["req_speed"]
                match_speed = False
                if current_speed == 'LS' and req == 'LS_REQ': match_speed = True
                elif current_speed == 'HS' and req in ['HS_REQ', 'MS_REQ']: match_speed = True
                elif current_speed == 'MS' and req in ['LS_REQ', 'MS_REQ']: match_speed = True # Из MS идем вниз или в горизонт
                
                if match_speed and not (physics["changes_axis"] and physics["family"] not in [1, 2, 5]):
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

        # АГРЕССИВНАЯ КОВКА МАКРОСА!
        final_macro = wrap_macro(fig["macro"], current_att, fig["exit_att"])

        sequence.append({
            "macro": final_macro, "speed_in": current_speed, "att_in": current_att, 
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
st.title("🏆 Unlimited Pro (Aresti Physics Matrix)")
st.write("Скрипт читает физику строго по кодам Арести и принудительно задает правильные входы/выходы каждому макросу, гарантируя 100% стыковку.")

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
