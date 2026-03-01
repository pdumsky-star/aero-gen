import streamlit as st
import random
import json

def load_database():
    try:
        with open('civa_database.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("❌ Файл civa_database.json не найден!")
        st.stop()

# ==========================================
# 1. ОЧИСТКА БАЗЫ ДАННЫХ (КРОСС-ЧЕК АРЕСТИ)
# ==========================================
def is_aligned_correctly(macro, aresti_list):
    """Отсеивает мусорные макросы, проверяя их соответствие кодам Арести"""
    if not aresti_list: return False
    family = int(aresti_list[0].split('.')[0])
    macro_lower = macro.lower()

    # Удаляем слова, случайно попавшие из текстов файлов
    bad_words = ["sequence", "generated", "unlimited", "training", "unknown", "advanced", "free", "known"]
    if any(w in macro_lower for w in bad_words): return False

    # Кросс-чек: База Арести должна совпадать с буквой OLAN
    if family == 2 and 'j' not in macro_lower: return False # Виражи
    if family == 5 and 'h' not in macro_lower: return False # Хаммерхеды
    if family == 6 and 'ta' not in macro_lower: return False # Колокола
    if family == 7 and not any(x in macro_lower for x in ['o', 'm', 'a', 'q', 'c']): return False # Петли
    if family == 8 and not any(x in macro_lower for x in ['c', 'b', 'p', 'u', 'g']): return False # Кубинцы, Бампы, P-петли

    return True

# ==========================================
# 2. МАТЕМАТИКА АЭРОДИНАМИКИ (ЧТЕНИЕ АРЕСТИ)
# ==========================================
def does_figure_change_axis(aresti_list):
    """Высчитывает смену оси X/Y, разбирая коды вращений 9.A.B.C"""
    changes = False
    for code in aresti_list:
        parts = code.split('.')
        if len(parts) == 4:
            family = int(parts[0])
            if family == 2:
                # Повороты на 90 (1) и 270 (3) меняют ось
                if parts[1] in ['1', '3']: changes = not changes 
            elif family == 9:
                line_dir = int(parts[2])
                amount = int(parts[3])
                # Если вращение на вертикали (3=вверх, 5=вниз) и оно нечетное (1/4, 3/4, 1.25), ось меняется
                if line_dir in [3, 5] and amount % 2 != 0:
                    changes = not changes
    return changes

def get_out_speed(aresti_list):
    """Вычисляет скорость на выходе из фигуры"""
    base_code = aresti_list[0]
    parts = base_code.split('.')
    family = int(parts[0])
    
    if family == 2: return "MS" # После виража скорость средняя
    if family == 7 and len(parts) > 2:
        sub = int(parts[1])
        if sub == 2 and parts[2] == '2': return "MS" # Иммельман
    return "HS" # Петли, вертикали и пикирования дают высокую скорость (HS)

def is_safe_for_hs(aresti_list):
    """Проверяет, можно ли выполнять фигуру после сильного разгона"""
    base_code = aresti_list[0]
    parts = base_code.split('.')
    family = int(parts[0])
    
    if family == 2: return False # Плоские виражи запрещены на HS
    if family == 1 and int(parts[1]) == 1: return False # Горизонтальные пролеты запрещены
    if family == 7 and int(parts[1]) == 2 and parts[2] == '3': return False # Split-S (вниз) запрещен
    return True

# ==========================================
# 3. ГЕНЕРАТОР КОМПЛЕКСОВ
# ==========================================
DATABASE = load_database()

def build_aerodynamic_data_sequence(length):
    sequence = []
    current_speed = "MS"
    current_axis = "X"
    figures_on_y = 0

    # 1. Фильтруем отравленную базу данных (выкидываем мусор от парсера)
    clean_pool = []
    for family, figs in DATABASE.items():
        for f in figs:
            if is_aligned_correctly(f["macro"], f["aresti"]):
                f["changes_axis"] = does_figure_change_axis(f["aresti"])
                f["safe_for_hs"] = is_safe_for_hs(f["aresti"])
                f["out_speed"] = get_out_speed(f["aresti"])
                clean_pool.append(f)

    if not clean_pool:
        st.error("В базе не осталось валидных фигур после очистки!")
        return []

    # 2. Собираем умный комплекс
    for i in range(length):
        valid_figs = []
        for f in clean_pool:
            # Правило 1: Энергия
            if current_speed == "HS" and not f["safe_for_hs"]: continue
            
            # Правило 2: Контроль поперечной оси (Y)
            if current_axis == "Y":
                # Запрещаем висеть на оси Y. Обязаны выбрать фигуру, возвращающую на X.
                if figures_on_y >= 1 and not f["changes_axis"]: continue 
            else:
                # Если мы на X, не уходим на Y в самом конце комплекса
                if f["changes_axis"] and i >= length - 2: continue 

            valid_figs.append(f)

        if not valid_figs:
            valid_figs = clean_pool # Failsafe

        fig = random.choice(valid_figs)

        sequence.append({
            "macro": fig["macro"],
            "aresti": ", ".join(fig["aresti"]),
            "speed_in": current_speed,
            "axis": current_axis,
            "changed_axis": fig["changes_axis"]
        })

        # Обновляем телеметрию
        current_speed = fig["out_speed"]
        if fig["changes_axis"]:
            current_axis = "Y" if current_axis == "X" else "X"

        if current_axis == "Y":
            figures_on_y += 1
        else:
            figures_on_y = 0

    # Failsafe: Если комплекс прервался на оси Y, принудительно возвращаем Хаммерхедом
    if current_axis == "Y":
        sequence.append({
            "macro": "1h",
            "aresti": "5.2.1.1, 9.1.5.1",
            "speed_in": "HS",
            "axis": "X",
            "changed_axis": True
        })

    return sequence

# --- Streamlit UI ---
st.set_page_config(page_title="Aero Gen DATA-PRO", page_icon="🛩️")
st.title("🏆 Аэродинамический Движок (Data-Driven PRO)")
st.write("Комплекс собирается из **реальных** кусков твоих файлов. Встроен санитарный фильтр, удаляющий ошибки парсинга, и математический движок расчета скоростей и осей.")

num_figs = st.sidebar.slider("Количество фигур", 5, 20, 10)

if st.button("Сгенерировать комплекс"):
    complex_data = build_aerodynamic_data_sequence(num_figs)
    final_string = " ".join([fig["macro"] for fig in complex_data])
    
    st.success("✅ Готово! Скопируй строку, вставь в OpenAero и нажми **Separate figures**.")
    st.code(final_string, language="text")
    
    st.write("### Телеметрия и происхождение фигур:")
    for i, fig in enumerate(complex_data):
        speed_icon = "🔥 HS" if fig["speed_in"] == "HS" else "💨 MS"
        axis_icon = "🔵 X" if fig["axis"] == "X" else "🔴 Y"
        turn_icon = " ↪️ (Уход на другую ось)" if fig["changed_axis"] else ""
        st.write(f"**{i+1}.** `{fig['macro']}` — *Арести: [{fig['aresti']}]*")
        st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;Вход: {speed_icon} | На оси: {axis_icon}{turn_icon}")
