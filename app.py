import streamlit as st
import random

# ==========================================
# 1. CIVA ВРАЩЕНИЯ (ИСПРАВЛЕННАЯ МАТЕМАТИКА)
# ==========================================
STAY_SINGLE = ["", "", "4", "44", "f", "88"]
FLIP_SINGLE = ["2", "24", "f2"]

# STAY = В сумме 360 градусов (самолет остается пузом вниз)
# Исправлено: 1/2 витка + 1/2 витка (2,24 и 24,2) теперь здесь!
STAY_LINKED = ["4,44", "f,4", "44,4", "2,24", "24,2", "f2,2"]

# FLIP = В сумме 180 или 540 градусов (самолет переворачивается на спину)
FLIP_LINKED = ["2,44", "4,2", "f,2", "24,44", "44,24"]

def get_mandatory_flip(speed, is_curved=False):
    valid = FLIP_SINGLE.copy()
    if not is_curved:
        valid.extend(FLIP_LINKED) 
    if speed == "HS":
        valid = [r for r in valid if "f" not in r] # Убираем штопорные на большой скорости
    return random.choice(valid)

def get_stay_roll(speed, is_curved=False):
    valid = STAY_SINGLE.copy()
    if not is_curved:
        valid.extend(STAY_LINKED)
    if speed == "HS":
        valid = [r for r in valid if "f" not in r]
    return random.choice(valid)

def get_y_roll():
    """Смена оси (90° или 270°) - только для безопасных вертикалей"""
    return random.choice(["1", "3", "3f", "14", "34"]) 

# ==========================================
# 2. ФИЗИКА ФИГУР 
# ==========================================
OPENAERO_DICTIONARY = [
    {"olan": "o",  "name": "Петля", "in_dir": "UP", "out_speed": "HS", "slots": [("top", "curved_stay")]},
    {"olan": "m",  "name": "Иммельман", "in_dir": "UP", "out_speed": "MS", "slots": [("exit", "mandatory_flip")]},
    {"olan": "a",  "name": "Split-S", "in_dir": "DOWN", "out_speed": "HS", "slots": [("entry", "mandatory_flip")]},
    {"olan": "c",  "name": "Half Cuban", "in_dir": "UP", "out_speed": "HS", "slots": [("exit", "mandatory_flip")]},
    {"olan": "rc", "name": "Reverse Cuban", "in_dir": "UP", "out_speed": "HS", "slots": [("entry", "mandatory_flip")]},
    # Для ухода на Y-ось разрешены только эти 3 фигуры:
    {"olan": "ta", "name": "Прямой колокол", "in_dir": "UP", "out_speed": "HS", "slots": [("entry", "vertical_y"), ("exit", "vertical_y")]},
    {"olan": "h",  "name": "Хаммерхед", "in_dir": "UP", "out_speed": "HS", "slots": [("entry", "vertical_y"), ("exit", "vertical_y")]},
    {"olan": "b",  "name": "Humpty Bump", "in_dir": "UP", "out_speed": "HS", "slots": [("entry", "vertical_y"), ("exit", "vertical_y")]},
    {"olan": "j",  "name": "Вираж 180", "in_dir": "HORIZ", "out_speed": "MS", "slots": []},
    # P-Loop больше не уходит на Y и использует только сохраняющие бочки на вертикали
    {"olan": "p",  "name": "P-Loop", "in_dir": "UP", "out_speed": "HS", "slots": [("entry", "vertical_stay"), ("exit", "horizontal")]},
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
            if current_speed == "HS" and fig["in_dir"] != "UP":
                continue
            has_vertical_y = any(t == "vertical_y" for _, t in fig["slots"])
            if current_axis == "Y" and figures_on_y >= 1 and not has_vertical_y:
                continue 
            valid_figs.append(fig)
            
        fig = random.choice(valid_figs)
        rolls = {"entry": "", "top": "", "exit": ""}
        
        has_vertical_y = any(t == "vertical_y" for _, t in fig["slots"])
        need_return_to_x = (current_axis == "Y" and has_vertical_y)
        go_to_y = (current_axis == "X" and has_vertical_y and random.random() < 0.25 and i < length - 2)
        axis_changed_in_this_fig = False
        
        for slot_pos, slot_type in fig["slots"]:
            if slot_type == "mandatory_flip":
                rolls[slot_pos] = get_mandatory_flip(current_speed, is_curved=False)
            elif slot_type == "horizontal":
                if random.random() < 0.4:
                    rolls[slot_pos] = get_stay_roll(current_speed, is_curved=False)
            elif slot_type == "curved_stay":
                if random.random() < 0.4:
                    rolls[slot_pos] = get_stay_roll(current_speed, is_curved=True)
            elif slot_type == "vertical_stay":
                # Безопасная вертикаль (например, P-Loop), крутим только 360
                if random.random() < 0.4:
                    rolls[slot_pos] = get_stay_roll(current_speed, is_curved=False)
            elif slot_type == "vertical_y":
                if (need_return_to_x or go_to_y) and not axis_changed_in_this_fig:
                    rolls[slot_pos] = get_y_roll()
                    axis_changed_in_this_fig = True
                    current_axis = "X" if current_axis == "Y" else "Y"
                    if current_axis == "X":
                        figures_on_y = 0
                else:
                    if not axis_changed_in_this_fig and random.random() < 0.4:
                        # Чтобы не ломать логику переворотов, на вертикалях крутим только 360
                        rolls[slot_pos] = get_stay_roll(current_speed, is_curved=False)
                        
        macro = f"{rolls.get('entry', '')}{fig['olan']}{rolls.get('top', '')}{rolls.get('exit', '')}"
        sequence.append({"macro": macro, "desc": fig["name"], "speed_in": current_speed, "axis": current_axis})
        current_speed = fig["out_speed"]
        if current_axis == "Y":
            figures_on_y += 1
            
    if current_axis == "Y":
        sequence.append({"macro": "1h", "desc": "Хаммерхед (Возврат на X)", "speed_in": "HS", "axis": "X"})
        
    return sequence

st.set_page_config(page_title="Aero Gen Engine", page_icon="🛩️")
st.title("🏆 Аэродинамический Движок (Fix Math & Axes)")
st.write("Исправлена математика комбинированных бочек и ограничена смена осей для сложных фигур.")

num_figs = st.sidebar.slider("Количество фигур", 5, 20, 10)

if st.button("Сгенерировать комплекс"):
    complex_data = build_aerodynamic_sequence(num_figs)
    final_string = " ".join([fig["macro"] for fig in complex_data])
    st.success("✅ Готово! Копируй строку, вставляй в OpenAero и нажимай **Separate figures**.")
    st.code(final_string, language="text")
