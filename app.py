import streamlit as st
import random
import json

def load_database():
    try:
        with open('civa_mega.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("❌ Файл civa_mega.json не найден! Запустите mega_builder.py")
        st.stop()

# ==========================================
# 1. СЛОВАРЬ ЛЕГАЛЬНЫХ ВРАЩЕНИЙ (Без "Ножей")
# ==========================================
SAFE_ROLLS = [
    {"macro": "", "k": 0, "flip": False},          # Пустой слот
    {"macro": "2", "k": 6, "flip": True},          # Полубочка
    {"macro": "4", "k": 12, "flip": False},        # Полная бочка
    {"macro": "22", "k": 12, "flip": False},       # 2 по 1/2 (бочка 2x2)
    {"macro": "44", "k": 16, "flip": False},       # 4 по 1/4 (бочка 4x4)
    {"macro": "24", "k": 9, "flip": True},         # 2 по 1/4 (полубочка 2x4)
    {"macro": "88", "k": 20, "flip": False},       # 8 по 1/8 (бочка 8x8)
]

# ==========================================
# 2. ДИНАМИЧЕСКАЯ СБОРКА ФИГУРЫ
# ==========================================
def assemble_figure(template):
    macro = template["macro"]
    k_total = template["k_factor"]
    flips_added = 0

    if "_" in macro:
        roll = random.choice(SAFE_ROLLS)
        macro = macro.replace("_", roll["macro"], 1)
        k_total += roll["k"]
        if roll["flip"]: flips_added += 1

    if "^" in macro:
        roll = random.choice(SAFE_ROLLS)
        macro = macro.replace("^", roll["macro"], 1)
        k_total += roll["k"]
        if roll["flip"]: flips_added += 1

    exit_att = template["exit_att"]
    if flips_added % 2 != 0:
        exit_att = "U" if exit_att == "I" else "I"

    assembled_fig = template.copy()
    assembled_fig["macro"] = macro
    assembled_fig["k_factor"] = k_total
    assembled_fig["exit_att"] = exit_att
    
    return assembled_fig

# ==========================================
# 3. ПАРАШЮТЫ
# ==========================================
def get_y_recovery_figure(att, speed):
    if speed == 'HS': return {"macro": "-h4-" if att == 'I' else "+h4+", "req_speed": "HS_REQ", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "Y", "k_factor": 25}
    elif speed == 'LS': return {"macro": "-iv4-" if att == 'I' else "+iv4+", "req_speed": "LS_REQ", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "Y", "k_factor": 15}
    else: return {"macro": "-1j-" if att == 'I' else "+1j+", "req_speed": "MS_REQ", "out_speed": "MS", "req_entry": att, "exit_att": att, "axis": "Y", "k_factor": 10}

def get_x_recovery_figure(att, speed):
    if speed == 'HS': return {"macro": "-o-" if att == 'I' else "+o+", "req_speed": "HS_REQ", "out_speed": "HS", "req_entry": att, "exit_att": att, "axis": "X", "k_factor": 12}
    elif speed == 'LS': return {"macro": "-a+" if att == 'I' else "+2a+", "req_speed": "LS_REQ", "out_speed": "HS", "req_entry": att, "exit_att": "U", "axis": "X", "k_factor": 15}
    else: return {"macro": "-j-" if att == 'I' else "+j+", "req_speed": "MS_REQ", "out_speed": "MS", "req_entry": att, "exit_att": att, "axis": "X", "k_factor": 10}

# ==========================================
# 4. ГЕНЕРАТОР КОМПЛЕКСОВ
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

    raw_pool = []
    for family, figs in DATABASE.items():
        for f in figs:
            if f["changes_axis"] and family != "2": continue
            raw_pool.append(f)

    if not raw_pool: return []

    for i in range(length):
        if current_axis == "Y":
            fig = get_y_recovery_figure(current_att, current_speed)
            sequence.append({
                "macro": fig["macro"], "speed_in": current_speed, "att_in": current_att, 
                "att_out": fig["exit_att"], "axis": "Y", "k_factor": fig["k_factor"]
            })
            current_att, current_speed, current_axis = fig["exit_att"], fig["out_speed"], "X"
            figures_since_y = 0
            current_k += fig["k_factor"]; link_count += 1; cons_hard = 0
            continue

        valid_templates = [f for f in raw_pool if f["req_entry"] == current_att]
        
        speed_filtered = []
        for f in valid_templates:
            req = f["req_speed"]
            if current_speed == 'HS' and req == 'HS_REQ': speed_filtered.append(f)
            elif current_speed == 'LS' and req == 'LS_REQ': speed_filtered.append(f)
            elif current_speed == 'MS' and req in ['MS_REQ', 'LS_REQ']: speed_filtered.append(f)
            
        valid_templates = speed_filtered

        if figures_since_y < 2 or i >= length - 2:
            valid_templates = [f for f in valid_templates if not f.get("changes_axis")]

        if valid_templates:
            # === ДИНАМИЧЕСКАЯ СБОРКА ЗДЕСЬ ===
            template = random.choice(valid_templates)
            fig = assemble_figure(template)
        else:
            fig = get_x_recovery_figure(current_att, current_speed)

        if fig["k_factor"] > link_threshold:
            hard_count += 1; cons_hard += 1
        else:
            link_count += 1; cons_hard = 0

        sequence.append({
            "macro": fig["macro"], "speed_in": current_speed, "att_in": current_att, 
            "att_out": fig["exit_att"], "axis": "X", "k_factor": fig["k_factor"]
        })

        current_att = fig["exit_att"] 
        current_speed = fig.get("out_speed", "MS")
        current_k += fig["k_factor"]
        
        if fig.get("changes_axis"):
            current_axis = "Y"; figures_since_y = 0
        else:
            figures_since_y += 1

    return sequence, current_k

# --- Streamlit UI ---
st.set_page_config(page_title="Unlimited World Champ", page_icon="🏆", layout="wide")
st.title("🏆 Unlimited Pro (Clean Mega-Base)")
st.write("База пересобрана на основе идеальной математики Арести. Генератор берет заготовки и динамически добавляет безопасные фиксации.")

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
