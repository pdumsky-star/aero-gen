import streamlit as st
import random

# ==========================================
# 1. CIVA ВРАЩЕНИЯ С УЧЕТОМ СКОРОСТИ
# ==========================================
# HS = High Speed (Скорость > 300 км/ч, штопорные нельзя)
# MS = Medium Speed (Скорость 180-220 км/ч, штопорные разрешены)

def get_mandatory_flip(speed):
    """180° вращения для выхода в прямой полет (U-to-U)"""
    if speed == "MS":
        return random.choice(["2", "24", "f2", "2,44"]) # Штопорные разрешены
    return random.choice(["2", "24", "2,44"]) # Только элеронные на большой скорости

def get_stay_roll(speed):
    """Вращения на 360°, сохраняющие прямое положение"""
    if speed == "MS":
        return random.choice(["4", "44", "f"]) 
    return random.choice(["4", "44"])

def get_y_roll():
    """Смена оси (90° или 270°) на вертикали"""
    return random.choice(["1", "3", "3f"]) # 3/4 штопорной на вертикали - частая практика

# ==========================================
# 2. ФИЗИКА ФИГУР (ENERGY MANAGEMENT)
# ==========================================
# in_dir: Требуемый вектор входа (UP, DOWN, HORIZ)
# out_speed: Скорость на выходе из фигуры
OPENAERO_DICTIONARY = [
    {"olan": "o",  "name": "Петля", "in_dir": "UP", "out_speed": "HS", "slots": [("top", "horizontal")]},
    {"olan": "m",  "name": "Иммельман", "in_dir": "UP", "out_speed": "MS", "slots": [("exit", "mandatory_flip")]},
    {"olan": "a",  "name": "Split-S (Переворот)", "in_dir": "DOWN", "out_speed": "HS", "slots": [("entry", "mandatory_flip")]},
    {"olan": "c",  "name": "Half Cuban", "in_dir": "UP", "out_speed": "HS", "slots": [("exit", "mandatory_flip")]},
    {"olan": "rc", "name": "Reverse Cuban", "in_dir": "UP", "out_speed": "HS", "slots": [("entry", "mandatory_flip")]},
    {"olan": "ta", "name": "Прямой колокол", "in_dir": "UP", "out_speed": "HS", "slots": [("entry", "vertical"), ("exit", "vertical")]},
    {"olan": "h",  "name": "Хаммерхед", "in_dir": "UP", "out_speed": "HS", "slots": [("entry", "vertical"), ("exit", "vertical")]},
    {"olan": "b",  "name": "Humpty Bump", "in_dir": "UP", "out_speed": "HS", "slots": [("entry", "vertical"), ("exit", "vertical")]},
    {"olan": "j",  "name": "Вираж 180", "in_dir": "HORIZ", "out_speed": "MS", "slots": []},
    {"olan": "4jio2", "name": "Rolling Circle (1 круг)", "in_dir": "HORIZ", "out_speed": "MS", "slots": []}
]

def build_aerodynamic_sequence(length):
    sequence = []
    
    # Стартовые условия
    current_speed = "MS" 
    current_axis = "X"
    figures_on_y = 0
    
    for i in range(length):
        valid_figs = []
        for fig in OPENAERO_DICTIONARY:
            # ПРАВИЛО 1: Управление энергией (Скорость)
            # После разгона (HS) можно лететь только ВВЕРХ (UP)
            if current_speed == "HS" and fig["in_dir"] != "UP":
                continue
                
            # ПРАВИЛО 2: Контроль поперечной оси (Cross-box)
            # Нельзя зависать на оси Y дольше одной фигуры. 
            has_vertical = any(t == "vertical" for _, t in fig["slots"])
            if current_axis == "Y" and figures_on_y >= 1 and not has_vertical:
                continue # Принудительно заставляем взять фигуру с вертикалью для возврата
                
            valid_figs.append(fig)
            
        fig = random.choice(valid_figs)
        rolls = {"entry": "", "top": "", "exit": ""}
        
        has_vertical = any(t == "vertical" for _, t in fig["slots"])
        need_return_to_x = (current_axis == "Y" and has_vertical)
        go_to_y = (current_axis == "X" and has_vertical and random.random() < 0.25 and i < length - 2)
        axis_changed = False
        
        # Расставляем бочки
        for slot_pos, slot_type in fig["slots"]:
            if slot_type == "mandatory_flip":
                rolls[slot_pos] = get_mandatory_flip(current_speed)
                
            elif slot_type == "horizontal":
                if random.random() < 0.3:
                    rolls[slot_pos] = get_stay_roll(current_speed)
                    
            elif slot_type == "vertical":
                # Обработка ухода/возврата на ось Y
                if (need_return_to_x or go_to_y) and not axis_changed:
                    rolls[slot_pos] = get_y_roll()
                    axis_changed = True
                    current_axis = "X" if current_axis == "Y" else "Y"
                    if current_axis == "X":
                        figures_on_y = 0
                else:
                    if random.random() < 0.3:
                        rolls[slot_pos] = random.choice(["4", "44"]) # 360-бочка на вертикали
                        
        macro = f"{rolls.get('entry', '')}{fig['olan']}{rolls.get('top', '')}{rolls.get('exit', '')}"
        
        sequence.append({
            "macro": macro, 
            "desc": fig["name"], 
            "speed_in": current_speed,
            "axis": current_axis
        })
        
        # Обновляем состояния
        current_speed = fig["out_speed"]
        if current_axis == "Y":
            figures_on_y += 1
            
    # Failsafe: принудительный возврат, если комплекс прервался на оси Y
    if current_axis == "Y":
        sequence.append({"macro": "1h", "desc": "Хаммерхед (Возврат на ось X)", "speed_in": "HS", "axis": "X"})
        
    return sequence

# --- Streamlit UI ---
st.set_page_config(page_title="Aero Gen Unlimited", page_icon="🛩️")
st.title("🏆 Аэродинамический OLAN Генератор")
st.write("Теперь генератор отслеживает управление энергией (Скорость) и жестко контролирует ось Y.")

num_figs = st.sidebar.slider("Количество фигур", 5, 20, 10)

if st.button("Сгенерировать комплекс"):
    complex_data = build_aerodynamic_sequence(num_figs)
    final_string = " ".join([fig["macro"] for fig in complex_data])
    
    st.success("✅ Готово! Копируй строку, вставляй в OpenAero и нажимай **Separate figures**.")
    st.code(final_string, language="text")
    
    st.write("### Телеметрия комплекса:")
    for i, fig in enumerate(complex_
