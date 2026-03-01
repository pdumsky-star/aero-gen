import streamlit as st
import random

# ==========================================
# 1. CIVA ВРАЩЕНИЯ (ОДИНОЧНЫЕ И КОМБИНИРОВАННЫЕ)
# ==========================================
# Одиночные вращения (Можно ставить ВЕЗДЕ, включая вершину петли)
STAY_SINGLE = ["", "", "4", "44", "f", "88"]
FLIP_SINGLE = ["2", "24", "f2"]

# Комбинированные вращения (ТОЛЬКО для прямых линий - горизонталь, вертикаль, 45)
STAY_LINKED = ["4,44", "f,4", "44,4"]
FLIP_LINKED = ["2,44", "2,24", "f,2", "24,2"]

def get_mandatory_flip(speed, is_curved=False):
    """180° вращения для выхода в прямой полет"""
    valid = FLIP_SINGLE.copy()
    if not is_curved:
        valid.extend(FLIP_LINKED) # Добавляем связки только для прямых линий
    
    # Energy Management: На большой скорости (HS) исключаем штопорные (f)
    if speed == "HS":
        valid = [r for r in valid if "f" not in r]
        
    return random.choice(valid)

def get_stay_roll(speed, is_curved=False):
    """Вращения на 360°, сохраняющие прямое положение"""
    valid = STAY_SINGLE.copy()
    if not is_curved:
        valid.extend(STAY_LINKED)
        
    if speed == "HS":
        valid = [r for r in valid if "f" not in r]
        
    return random.choice(valid)

def get_y_roll():
    """Смена оси (90° или 270°) - только на вертикалях (прямые линии)"""
    return random.choice(["1", "3", "3f", "14", "34"]) 

def get_safe_vert_roll():
    """Безопасные вращения на вертикали, НЕ меняющие ось (180/360)"""
    return random.choice(["2", "44", "24", "f", "2,44", "f,2"])

# ==========================================
# 2. ФИЗИКА ФИГУР (ENERGY MANAGEMENT & CURVES)
# ==========================================
OPENAERO_DICTIONARY = [
    # Вершина петли - это КРИВАЯ линия (curved). Комбинированные бочки ЗАПРЕЩЕНЫ.
    {"olan": "o",  "name": "Петля", "in_dir": "UP", "out_speed": "HS", "slots": [("top", "curved_stay")]},
    # Все остальные слоты ниже - это ПРЯМЫЕ линии. На них можно всё.
    {"olan": "m",  "name": "Иммельман", "in_dir": "UP", "out_speed": "MS", "slots": [("exit", "mandatory_flip")]},
    {"olan": "a",  "name": "Split-S", "in_dir": "DOWN", "out_speed": "HS", "slots": [("entry", "mandatory_flip")]},
    {"olan": "c",  "name": "Half Cuban", "in_dir": "UP", "out_speed": "HS", "slots": [("exit", "mandatory_flip")]},
    {"olan": "rc", "name": "Reverse Cuban", "in_dir": "UP", "out_speed": "HS", "slots": [("entry", "mandatory_flip")]},
    {"olan": "ta", "name": "Прямой колокол", "in_dir": "UP", "out_speed": "HS", "slots": [("entry", "vertical"), ("exit", "vertical")]},
    {"olan": "h",  "name": "Хаммерхед", "in_dir": "UP", "out_speed": "HS", "slots": [("entry", "vertical"), ("exit", "vertical")]},
    {"olan": "b",  "name": "Humpty Bump", "in_dir": "UP", "out_speed": "HS", "slots": [("entry", "vertical"), ("exit", "vertical")]},
    {"olan": "j",  "name": "Вираж 180", "in_dir": "HORIZ", "out_speed": "MS", "slots": []},
    {"olan": "p",  "name": "P-Loop", "in_dir": "UP", "out_speed": "HS", "slots": [("entry", "vertical"), ("exit", "mandatory_flip")]},
    {"olan": "4jio2", "name": "Rolling Circle (1 круг)", "in_dir": "HORIZ", "out_speed": "MS", "slots": []}
]

def build_aerodynamic_sequence(length):
    sequence = []
    current_speed = "MS" 
    current_axis = "X"
    figures_on_y = 0
    
    for i in range(length):
        valid_figs = []
        for fig in OPENAERO_DICTIONARY:
            # ПРАВИЛО 1: Энергия. После пикирования (HS) летим только вверх.
            if current_speed == "HS" and fig["in_dir"] != "UP":
                continue
            # ПРАВИЛО 2: Блокировка зависания на Y-оси.
            has_vertical = any(t == "vertical" for _, t in fig["slots"])
            if current_axis == "Y" and figures_on_y >= 1 and not has_vertical:
                continue 
            valid_figs.append(fig)
            
        fig = random.choice(valid_figs)
        rolls = {"entry": "", "top": "", "exit": ""}
        
        has_vertical = any(t == "vertical" for _, t in fig["slots"])
        need_return_to_x = (current_axis == "Y" and has_vertical)
        go_to_y = (current_axis == "X" and has_vertical and random.random() < 0.25 and i < length - 2)
        axis_changed_in_this_fig = False
        
        for slot_pos, slot_type in fig["slots"]:
            if slot_type == "mandatory_flip":
                # Прямая линия, разрешаем всё
                rolls[slot_pos] = get_mandatory_flip(current_speed, is_curved=False)
                
            elif slot_type == "curved_stay":
                if random.random() < 0.4:
                    # Кривая линия, разрешаем только одиночные вращения
                    rolls[slot_pos] = get_stay_roll(current_speed, is_curved=True)
                    
            elif slot_type == "vertical":
                if (need_return_to_x or go_to_y) and not axis_changed_in_this_fig:
                    rolls[slot_pos] = get_y_roll()
                    axis_changed_in_this_fig = True
                    current_axis = "X" if current_axis == "Y" else "Y"
                    if current_axis == "X":
                        figures_on_y = 0
                else:
                    if not axis_changed_in_this_fig:
                        if random.random() < 0.4:
                            rolls[slot_pos] = get_safe_vert_roll()
                        
        macro = f"{rolls.get('entry', '')}{fig['olan']}{rolls.get('top', '')}{rolls.get('exit', '')}"
        sequence.append({
            "macro": macro, 
            "desc": fig["name"], 
            "speed_in": current_speed,
            "axis": current_axis
        })
        
        current_speed = fig["out_speed"]
        if current_axis == "Y":
            figures_on_y += 1
            
    # Failsafe: Возврат на X
    if current_axis == "Y":
        sequence.append({"macro": "1h", "desc": "Хаммерхед (Возврат на X)", "speed_in": "HS", "axis": "X"})
        
    return sequence

# --- Streamlit UI ---
st.set_page_config(page_title="Aero Gen Engine", page_icon="🛩️")
st.title("🏆 Аэродинамический Движок (CIVA PRO)")
st.write("Теперь генератор понимает геометрию фигур. Комбинированные бочки (со сменой направления) разрешены только на прямых линиях. На кривых линиях (петлях) используются только мощные одиночные вращения.")

num_figs = st.sidebar.slider("Количество фигур", 5, 20, 10)

if st.button("Сгенерировать комплекс"):
    complex_data = build_aerodynamic_sequence(num_figs)
    final_string = " ".join([fig["macro"] for fig in complex_data])
    
    st.success("✅ Готово! Копируй строку, вставляй в OpenAero и нажимай **Separate figures**.")
    st.code(final_string, language="text")
