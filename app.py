import streamlit as st
import random

# ==========================================
# 1. CIVA ВАЛИДНЫЕ ВРАЩЕНИЯ (OLAN)
# ==========================================
# Вращения, меняющие положение (Прямое <-> Перевернутое) на горизонталях и 45-линиях
ROLL_FLIP = ["2", "6", "24", "f2"] 
# Вращения, сохраняющие положение
ROLL_STAY = ["4", "8", "44", "88", "f"]
# Вращения, меняющие ось Y (только для вертикалей)
ROLL_AXIS = ["1", "3", "14", "34"]

# Валидные связки (Linked Rolls) со сменой направления через запятую
LINKED_FLIP = ["2,24", "24,2", "f,2", "4,2", "2,44"]
LINKED_STAY = ["2,2", "4,44", "2,f2", "f,4"]
LINKED_AXIS = ["2,1", "1,2", "14,2", "f,1"]

# ==========================================
# 2. БАЗА ФИГУР С УЧЕТОМ ФИЗИКИ ПОЛЕТА
# ==========================================
# in_att: Требуемый вход (U - Upright, I - Inverted, Any - любой)
# base_flip: Переворачивает ли сама геометрия фигуры самолет (Например, полупетля m переворачивает)
# mandatory: Слот, куда ОБЯЗАТЕЛЬНО нужно поставить бочку по правилам Aresti
OPENAERO_DICTIONARY = [
    {"olan": "o",  "name": "Петля", "in_att": "Any", "base_flip": False, "slots": {"top": "horiz"}},
    {"olan": "m",  "name": "Immelmann (Полупетля вверх)", "in_att": "U", "base_flip": True, "slots": {"exit": "horiz"}},
    {"olan": "a",  "name": "Split-S (Переворот)", "in_att": "I", "base_flip": True, "slots": {"entry": "horiz"}},
    {"olan": "rc", "name": "Reverse Half Cuban", "in_att": "U", "base_flip": True, "slots": {"entry": "45"}, "mandatory": "entry"},
    {"olan": "c",  "name": "Half Cuban", "in_att": "U", "base_flip": True, "slots": {"exit": "45"}, "mandatory": "exit"},
    {"olan": "j",  "name": "Вираж 180", "in_att": "Any", "base_flip": False, "slots": {}},
    {"olan": "ta", "name": "Прямой колокол", "in_att": "Any", "base_flip": False, "slots": {"entry": "vert", "exit": "vert"}},
    {"olan": "h",  "name": "Хаммерхед", "in_att": "Any", "base_flip": False, "slots": {"entry": "vert", "exit": "vert"}},
    {"olan": "b",  "name": "Humpty Bump", "in_att": "Any", "base_flip": False, "slots": {"entry": "vert", "top": "horiz", "exit": "vert"}},
    {"olan": "p",  "name": "P-Loop", "in_att": "Any", "base_flip": False, "slots": {"entry": "vert", "exit": "horiz"}},
    {"olan": "rp", "name": "Reverse P-Loop", "in_att": "Any", "base_flip": False, "slots": {"entry": "horiz", "exit": "vert"}},
    {"olan": "4jio2", "name": "Rolling Circle (1 круг, 4 бочки)", "in_att": "U", "base_flip": False, "slots": {}}
]

def build_smart_sequence(length):
    sequence = []
    current_att = 'U'  # Начинаем в прямом полете (Upright)
    current_axis = 'X' # Начинаем по главной оси квадрата
    
    for _ in range(length):
        # 1. Фильтруем фигуры, в которые мы физически можем войти
        valid_figs = []
        for fig in OPENAERO_DICTIONARY:
            if fig['in_att'] != 'Any' and current_att != fig['in_att']:
                # Если позиция не совпадает, фигура обязана иметь entry-слот для корректирующей бочки
                if 'entry' not in fig['slots']:
                    continue
                # Бочка на вертикали не переворачивает самолет (U/I), поэтому она не спасет
                if fig['slots']['entry'] == 'vert':
                    continue
            valid_figs.append(fig)
            
        fig = random.choice(valid_figs)
        fig_att = current_att
        rolls = {"entry": "", "top": "", "exit": ""}
        
        # 2. Обработка ВХОДА (Entry)
        if 'entry' in fig['slots']:
            line = fig['slots']['entry']
            needs_flip = False
            
            # Если нужно перевернуться для правильного входа (например, из U в I для Split-S)
            if fig['in_att'] != 'Any' and fig_att != fig['in_att']:
                needs_flip = True
            # Если фигура жестко требует бочку (Reverse Cuban)
            if fig.get('mandatory') == 'entry':
                needs_flip = True
                
            axis_change = (line == 'vert' and random.random() < 0.25)
            
            if needs_flip:
                rolls['entry'] = random.choice(ROLL_FLIP + LINKED_FLIP)
                # Бочка на вертикали не меняет U/I при выходе в горизонт!
                if line != 'vert': 
                    fig_att = 'I' if fig_att == 'U' else 'U'
            elif axis_change:
                rolls['entry'] = random.choice(ROLL_AXIS + LINKED_AXIS)
                current_axis = 'Y' if current_axis == 'X' else 'X'
            elif random.random() < 0.3:
                rolls['entry'] = random.choice(ROLL_STAY + LINKED_STAY)

        # 3. Влияние самой геометрии фигуры на положение (U/I)
        if fig['base_flip']:
            fig_att = 'I' if fig_att == 'U' else 'U'

        # 4. Обработка ВЕРШИНЫ (Top)
        if 'top' in fig['slots']:
            if random.random() < 0.3:
                if random.random() < 0.5:
                    rolls['top'] = random.choice(ROLL_FLIP + LINKED_FLIP)
                    fig_att = 'I' if fig_att == 'U' else 'U'
                else:
                    rolls['top'] = random.choice(ROLL_STAY + LINKED_STAY)

        # 5. Обработка ВЫХОДА (Exit)
        if 'exit' in fig['slots']:
            line = fig['slots']['exit']
            needs_flip = False
            
            if fig.get('mandatory') == 'exit':
                needs_flip = True
                
            axis_change = (line == 'vert' and random.random() < 0.25)
            
            if needs_flip:
                rolls['exit'] = random.choice(ROLL_FLIP + LINKED_FLIP)
                if line != 'vert':
                    fig_att = 'I' if fig_att == 'U' else 'U'
            elif axis_change:
                rolls['exit'] = random.choice(ROLL_AXIS + LINKED_AXIS)
                current_axis = 'Y' if current_axis == 'X' else 'X'
            elif random.random() < 0.3:
                if random.random() < 0.5:
                    rolls['exit'] = random.choice(ROLL_FLIP + LINKED_FLIP)
                    if line != 'vert':
                        fig_att = 'I' if fig_att == 'U' else 'U'
                else:
                    rolls['exit'] = random.choice(ROLL_STAY + LINKED_STAY)

        # 6. Сохраняем состояние для следующей фигуры
        current_att = fig_att
        macro = f"{rolls['entry']}{fig['olan']}{rolls['top']}{rolls['exit']}"
        
        sequence.append({
            "macro": macro,
            "desc": fig['name'],
            "att": current_att,
            "axis": current_axis
        })
        
    return sequence

# --- Streamlit UI ---
st.set_page_config(page_title="Unlimited OLAN PRO", page_icon="🛩️")
st.title("🏆 Валидный OLAN Генератор (PRO)")
st.write("Скрипт отслеживает положение самолета (Прямой/Перевернутый) и гарантирует правильные бочки для Half Cuban, Reverse Cuban и Split-S.")

num_figs = st.sidebar.slider("Количество фигур", 5, 20, 10)

if st.button("Сгенерировать комплекс"):
    complex_data = build_smart_sequence(num_figs)
    
    # Теперь нам не нужны ручные отступы (0,5), так как в OpenAero есть кнопка Separate figures
    final_string = " ".join([fig["macro"] for fig in complex_data])
    
    st.success("✅ Готово! Скопируй строку, вставь в OpenAero и нажми кнопку **Separate figures**.")
    st.code(final_string, language="text")
    
    st.write("### Логика полета (Телеметрия):")
    for i, fig in enumerate(complex_data):
        att_icon = "⬆️ Прямой" if fig["att"] == "U" else "⬇️ Перевернутый"
        axis_icon = "🔵 X" if fig["axis"] == "X" else "🔴 Y"
        st.write(f"**{i+1}.** `{fig['macro']}` — {fig['desc']} *(Выход: {att_icon}, Ось: {axis_icon})*")
