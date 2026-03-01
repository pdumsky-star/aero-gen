import streamlit as st
import random

# ==========================================
# БАЗА ЗНАНИЙ OLAN (OpenAero + CIVA Rules)
# ==========================================

# Вращения, сохраняющие текущую ось (кратные 180°)
NON_AXIS_ROLLS = ["2", "4", "24", "44", "88", "f", "2f", "if", "2if"]

# Вращения, МЕНЯЮЩИЕ ось полета на перпендикулярную (90°, 270°)
AXIS_ROLLS = ["1", "3", "34", "3f", "3if"]

# Точная база OLAN с указанием доступных линий (slots)
OPENAERO_DICTIONARY = [
    {"olan": "o",  "name": "Петля", "slots": {"top": "horiz"}},
    {"olan": "m",  "name": "Полупетля вверх (Immelmann)", "slots": {"exit": "horiz"}},
    {"olan": "a",  "name": "Переворот (Split-S)", "slots": {"entry": "horiz"}},
    {"olan": "rc", "name": "Reverse Half Cuban", "slots": {"entry": "45"}},
    {"olan": "c",  "name": "Half Cuban", "slots": {"exit": "45"}},
    {"olan": "j",  "name": "Вираж 180", "slots": {}},
    {"olan": "ta", "name": "Прямой колокол (Tail Slide)", "slots": {"entry": "vert", "exit": "vert"}},
    {"olan": "h",  "name": "Хаммерхед", "slots": {"entry": "vert", "exit": "vert"}},
    {"olan": "b",  "name": "Humpty Bump", "slots": {"entry": "vert", "top": "horiz", "exit": "vert"}},
    {"olan": "p",  "name": "P-Loop", "slots": {"entry": "vert"}},
    {"olan": "rp", "name": "Reverse P-Loop", "slots": {"exit": "vert"}},
]

def generate_valid_roll(line_type, force_axis_change=False):
    """Генерация строго валидного по правилам CIVA вращения"""
    if force_axis_change:
        # Для смены оси берем вращение на 90 или 270 градусов
        return random.choice(AXIS_ROLLS)
    else:
        # Без смены оси: кратные 180 градусам (чтобы не лететь на ноже)
        r1 = random.choice(NON_AXIS_ROLLS)
        
        # 30% шанс на двойное вращение (СТРОГО со сменой направления через запятую)
        # Например: '2,44' - полбочки, затем противоположная на 4 фиксации
        if random.random() < 0.3:
            r2 = random.choice(NON_AXIS_ROLLS)
            return f"{r1},{r2}"
        return r1

def build_complex(length):
    sequence = []
    current_axis = 'X' # Начинаем полет по главной оси
    
    for i in range(length):
        base = random.choice(OPENAERO_DICTIONARY)
        
        # Проверяем, есть ли у фигуры вертикальные линии (только на них можно менять ось)
        vert_slots = [s for s, t in base["slots"].items() if t == "vert"]
        change_axis_here = False
        
        if vert_slots:
            # 25% шанс уйти в поперечную коробку (ось Y)
            if current_axis == 'X' and random.random() < 0.25:
                change_axis_here = True
            # 60% шанс вернуться обратно на X, если мы уже на Y
            elif current_axis == 'Y' and random.random() < 0.6:
                change_axis_here = True
                
        # Если это конец комплекса, принудительно возвращаем самолет на главную ось (X)
        if current_axis == 'Y' and i >= length - 2 and vert_slots:
            change_axis_here = True

        figure_rolls = {"entry": "", "top": "", "exit": ""}
        axis_changed_in_this_figure = False
        
        for slot, line_type in base["slots"].items():
            # Если решили менять ось — ставим 1/4 или 3/4 вращения на вертикаль
            if change_axis_here and slot == vert_slots[0] and not axis_changed_in_this_figure:
                figure_rolls[slot] = generate_valid_roll(line_type, force_axis_change=True)
                axis_changed_in_this_figure = True
                current_axis = 'Y' if current_axis == 'X' else 'X'
            else:
                # Обычное вращение (шанс 40%)
                if random.random() < 0.4:
                    figure_rolls[slot] = generate_valid_roll(line_type, force_axis_change=False)
                    
        # Сборка финального OLAN-кода фигуры (Входная бочка + База + Верхняя бочка + Выходная бочка)
        macro = f"{figure_rolls.get('entry', '')}{base['olan']}{figure_rolls.get('top', '')}{figure_rolls.get('exit', '')}"
        
        sequence.append({
            "macro": macro,
            "desc": base["name"],
            "axis": current_axis
        })
        
    return sequence

# --- Streamlit UI ---
st.set_page_config(page_title="Unlimited OLAN Gen", page_icon="✈️")
st.title("🏆 Валидный OLAN Генератор (CIVA Rules)")
st.write("Генерирует макро-код со строгим соблюдением правил комбинирования бочек и отслеживанием поперечной оси (Y).")

num_figs = st.sidebar.slider("Количество фигур", 5, 20, 10)

if st.button("Сгенерировать комплекс"):
    complex_data = build_complex(num_figs)
    final_string = " ".join([fig["macro"] for fig in complex_data])
    
    st.success("✅ Готово! Вставь строку в верхнее поле OpenAero, нажми Enter, а затем используй кнопку **Separate figures**.")
    st.code(final_string, language="text")
    
    st.write("### Логика построения (для проверки):")
    for i, fig in enumerate(complex_data):
        axis_color = "🔴" if fig["axis"] == "Y" else "🔵"
        st.write(f"**{i+1}.** `{fig['macro']}` — {fig['desc']} (Ось выхода: {axis_color} {fig['axis']})")
