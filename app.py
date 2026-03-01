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
# 1. ЖЕСТКИЙ САНИТАРНЫЙ ФИЛЬТР
# ==========================================
def is_native_default(macro, aresti_list):
    """Отсеивает фигуры, где макрос не совпадает с дефолтной базой OpenAero"""
    if not aresti_list: return False
    base = aresti_list[0]
    m_lower = macro.lower()

    # Убиваем мусорные слова из текстов
    if any(w in m_lower for w in ["sequence", "generated", "unknown", "training", "unlimited", "free", "known"]): 
        return False
        
    # Очищаем макрос от служебных символов чисто для проверки букв
    m_letters = re.sub(r'[^a-z]', '', m_lower)

    # Проверка строгого соответствия макроса и Арести (защита от рассинхрона)
    if 'rc' in m_letters: return base.startswith('8.5.2') # Только Half Reverse Cuban
    if 'c' in m_letters and 'rc' not in m_letters: return base.startswith('8.5.6') or base.startswith('8.5.5')
    if 'm' in m_letters: return base.startswith('7.2.2')
    if 'a' in m_letters and not any(x in m_letters for x in ['ta','ia']): return base.startswith('7.2.3')
    if 'o' in m_letters and not any(x in m_letters for x in ['qo', 'jo']): return base.startswith('7.4.1')
    if 'qo' in m_letters: return base.startswith('7.4.3')
    if 'db' in m_letters: return base.startswith('8.4.15') or base.startswith('8.4.16') or base.startswith('8.4.17') or base.startswith('8.4.18')
    if 'b' in m_letters and 'db' not in m_letters: return base.startswith('8.4.1') or base.startswith('8.4.2')
    if 'h' in m_letters and 'dh' not in m_letters: return base.startswith('5.2.1')
    if 'ta' in m_letters: return base.startswith('6.2.1') or base.startswith('6.2.2')
    if 'rp' in m_letters: return base.startswith('8.6.1') or base.startswith('8.6.2') or base.startswith('8.6.3') or base.startswith('8.6.4')
    if 'p' in m_letters and 'rp' not in m_letters: return base.startswith('8.6.5') or base.startswith('8.6.6') or base.startswith('8.6.7') or base.startswith('8.6.8')
    if 'j' in m_letters: return base.startswith('2.')
    
    return True

# ==========================================
# 2. МАТЕМАТИКА АЭРОДИНАМИКИ
# ==========================================
def does_figure_change_axis(aresti_list):
    changes = False
    for code in aresti_list:
        parts = code.split('.')
        if len(parts) == 4:
            if int(parts[0]) == 2 and parts[1] in ['1', '3']: changes = not changes 
            elif int(parts[0]) == 9:
                if int(parts[2]) in [3, 5] and int(parts[3]) % 2 != 0: changes = not changes
    return changes

def get_out_speed(aresti_list):
    base = aresti_list[0]
    if base.startswith('2.') or base.startswith('7.2.2.') or base.startswith('8.6.5.') or base.startswith('8.6.6.'): 
        return "MS"
    return "HS"

def is_safe_for_hs(aresti_list):
    base = aresti_list[0]
    if base.startswith('2.') or base.startswith('7.2.3.'): return False
    return True

# ==========================================
# 3. ГЕНЕРАТОР
# ==========================================
DATABASE = load_database()

def build_aerodynamic_data_sequence(length):
    sequence = []
    current_speed = "MS"
    current_axis = "X"
    figures_on_y = 0

    # 1. Фильтруем базу
    clean_pool = []
    for family, figs in DATABASE.items():
        for f in figs:
            if is_native_default(f["macro"], f["aresti"]):
                f["changes_axis"] = does_figure_change_axis(f["aresti"])
                f["safe_for_hs"] = is_safe_for_hs(f["aresti"])
                f["out_speed"] = get_out_speed(f["aresti"])
                clean_pool.append(f)

    if not clean_pool:
        st.error("В базе не осталось валидных фигур! Убедитесь, что запустили новый parser.py")
        return []

    # 2. Собираем комплекс
    for i in range(length):
        valid_figs = []
        for f in clean_pool:
            if current_speed == "HS" and not f["safe_for_hs"]: continue
            if current_axis == "Y" and figures_on_y >= 1 and not f["changes_axis"]: continue 
            if current_axis == "X" and f["changes_axis"] and i >= length - 2: continue 
            valid_figs.append(f)

        if not valid_figs: valid_figs = clean_pool 

        fig = random.choice(valid_figs)

        sequence.append({
            "macro": fig["macro"],
            "aresti": ", ".join(fig["aresti"]),
            "speed_in": current_speed,
            "axis": current_axis,
            "changed_axis": fig["changes_axis"]
        })

        current_speed = fig["out_speed"]
        if fig["changes_axis"]: current_axis = "Y" if current_axis == "X" else "X"
        
        if current_axis == "Y": figures_on_y += 1
        else: figures_on_y = 0

    if current_axis == "Y":
        sequence.append({"macro": "1h", "aresti": "5.2.1.1, 9.1.5.1", "speed_in": "HS", "axis": "X", "changed_axis": True})

    return sequence

# --- Streamlit UI ---
st.set_page_config(page_title="Aero Gen DATA-PRO", page_icon="🛩️")
st.title("🏆 Аэродинамический Движок (Data-Driven PRO)")
st.write("Сборка из проверенных турнирных связок. Встроен математический фильтр защиты от рассинхрона OpenAero.")

num_figs = st.sidebar.slider("Количество фигур", 5, 20, 10)

if st.button("Сгенерировать комплекс"):
    complex_data = build_aerodynamic_data_sequence(num_figs)
    final_string = " ".join([fig["macro"] for fig in complex_data])
    
    st.success("✅ Готово! Скопируй строку, вставь в OpenAero и нажми **Separate figures**.")
    st.code(final_string, language="text")
    
    st.write("### Происхождение фигур:")
    for i, fig in enumerate(complex_data):
        speed_icon = "🔥 HS" if fig["speed_in"] == "HS" else "💨 MS"
        axis_icon = "🔵 X" if fig["axis"] == "X" else "🔴 Y"
        turn_icon = " ↪️ (Уход на другую ось)" if fig["changed_axis"] else ""
        st.write(f"**{i+1}.** `{fig['macro']}` — *Арести: [{fig['aresti']}]*")
        st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;Вход: {speed_icon} | На оси: {axis_icon}{turn_icon}")
