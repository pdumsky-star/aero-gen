import streamlit as st
import random
import json

def load_database():
    try:
        with open('civa_mega.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("❌ Файл civa_mega.json не найден! Запусти mega_builder.py")
        st.stop()

# ==========================================
# 1. БИБЛИОТЕКА ЛЕГАЛЬНЫХ ВРАЩЕНИЙ CIVA (БЕЗ "НОЖЕЙ")
# Взято на основе правил rules-civa.js
# ==========================================
SAFE_ROLLS = {
    "": {"macro": "", "k": 0, "flip": False},          # Пустой слот (без вращения)
    "2": {"macro": "2", "k": 6, "flip": True},         # Полубочка (переворачивает)
    "4": {"macro": "4", "k": 12, "flip": False},       # Полная бочка (360°)
    "22": {"macro": "22", "k": 12, "flip": False},     # 2 по 1/2 (полная бочка 2x2)
    "44": {"macro": "44", "k": 16, "flip": False},     # 4 по 1/4 (полная бочка 4x4)
    "24": {"macro": "24", "k": 9, "flip": True},       # 2 по 1/4 (полубочка с фиксацией 2x4)
    "88": {"macro": "88", "k": 20, "flip": False},     # 8 по 1/8 (полная бочка 8x8)
}

# ==========================================
# 2. ДИНАМИЧЕСКИЙ СБОРЩИК ФИГУР
# ==========================================
def assemble_figure(template):
    """Берет шаблон, находит слоты _ и ^, и навешивает бочки"""
    macro = template["macro"]
    k_total = template["k_factor"]
    flips_added = 0

    # Обработка первого слота (если есть)
    if "_" in macro:
        roll = random.choice(list(SAFE_ROLLS.values()))
        macro = macro.replace("_", roll["macro"], 1)
        k_total += roll["k"]
        if roll["flip"]: flips_added += 1

    # Обработка второго слота (если есть)
    if "^" in macro:
        roll = random.choice(list(SAFE_ROLLS.values()))
        macro = macro.replace("^", roll["macro"], 1)
        k_total += roll["k"]
        if roll["flip"]: flips_added += 1

    # Инвертируем выходное положение, если навесили нечетное количество полубочек
    exit_att = template["exit_att"]
    if flips_added % 2 != 0:
        exit_att = "U" if exit_att == "I" else "I"

    assembled_fig = template.copy()
    assembled_fig["macro"] = macro
    assembled_fig["k_factor"] = k_total
    assembled_fig["exit_att"] = exit_att
    
    return assembled_fig

# ==========================================
# 3. ПАРАШЮТЫ С ОСЕЙ
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

    # Вытаскиваем все сырые шаблоны (из civa_mega.json)
    raw_pool = []
    for family, figs in DATABASE.items():
        for f in figs:
            # Разрешаем менять ось только для виражей (Family 2)
            if f["changes_axis"] and family != "2": continue
            raw_pool.append(f)

    if not raw_pool:
        st.error("В базе нет фигур!")
        return []

    for i in range(length):
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

        valid_templates = [f for f in raw_pool if f["req_entry"] == current_att]
        
        # СТРОГАЯ СТЫКОВКА СКОРОСТЕЙ
        speed_filtered = []
        for f in valid_templates:
            req = f["req_speed"]
            if current_speed == 'HS' and req == 'HS_REQ': speed_filtered.append(f)
            elif current_speed == 'LS' and req == 'LS_REQ': speed_filtered.append(f)
            elif current_speed == 'MS' and req in ['MS_REQ', 'LS_REQ']: speed_filtered.append(f)
            
        valid_templates = speed_filtered

        if figures_since_y < 2 or i >= length - 2:
            valid_templates = [f for f in valid_templates if not f.get("changes_axis")]

        # ВЫБИРАЕМ ШАБЛОН И СОБИРАЕМ ЕГО С БОЧКАМИ
        if valid_templates:
            template = random.choice(valid_templates)
            fig = assemble_figure(template)
        else:
            fig = get_x_recovery_figure(current_att, current_speed)

        # Контроль K-Фактора
        if fig["k_factor"] > link_threshold:
            hard_count += 1; cons_hard += 1
        else:
            link_count += 1; cons_hard = 0

        sequence.append({
            "macro": fig["macro"], "speed_in": current_speed, "att_in": current_att, 
            "att_out": fig["exit_att"], "req_speed": fig.get("req_speed", ""), "axis": "X", "k_factor": fig["k_factor"]
        })

        current_att = fig["exit_att"] 
        current_speed = fig["out_speed"]
        current_k += fig["k_factor"]
        
        if fig.get("changes_axis"):
            current_axis = "Y"; figures_since_y = 0
        else:
            figures_since_y += 1

    return sequence, current_k

# --- Streamlit UI ---
st.set_page_config(page_title="Unlimited World Champ", page_icon="🏆", layout="wide")
st.title("🏆 Unlimited Pro (Dynamic CIVA Assembly)")
st.write("Скрипт берет голые шаблоны из `civa_mega.json` и динамически заменяет слоты `_` и `^` на разрешенные бочки CIVA (22, 44, 4), избегая полетов на ноже.")

st.sidebar.header("🛠 Бюджет CIVA")
num_hard = st.sidebar.slider("Боевые фигуры (Сложные)", 5, 12, 10)
num_link = st.sidebar.slider("Связочные фигуры (Простые)", 2, 6, 4)
max_k_total = st.sidebar.slider("Лимит сложности (Max Total K)", 300, 500, 420)
link_threshold = st.sidebar.slider("Порог K-фактора (Связочная <= K)", 10, 35, 25)

if st.button("Сгенерировать комплекс"):
    complex_data, total_k = build_tournament_sequence(num_hard, num_link, max_k_total, link_threshold)
    
    # Склеиваем макросы через пробел для вставки в OpenAero
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
        st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;Вход: {att_in} ({spd_icon}) ➡️ Выход: {'⬆️ Прямо' if fig['att_out'] == 'U' else '⬇️ Спина'} | Ось: {fig.get('axis', 'X')}")
