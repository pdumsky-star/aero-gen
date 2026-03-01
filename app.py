import streamlit as st
import random

# ==========================================
# 1. АТОМАРНЫЕ ВРАЩЕНИЯ OLAN (CIVA Valid)
# ==========================================
# Вращения, сохраняющие положение (0 или 360 градусов) - взвешены в сторону "без вращения"
STAY_ROLLS = ["", "", "", "4", "44", "f"] 

# Вращения, меняющие положение (Прямой <-> Перевернутый, 180 градусов)
FLIP_ROLLS = ["2", "24", "f2", "2,44", "4,2"]

# Вращения для смены оси (Cross-box, 90 или 270 градусов)
Y_ROLLS = ["1", "3"]

# ==========================================
# 2. БАЗА ФИГУР С ЖЕСТКИМИ ПРАВИЛАМИ СЛОТОВ
# ==========================================
# mandatory_flip: Слот, куда ОБЯЗАТЕЛЬНО нужно поставить 180-градусное вращение, чтобы фигура вышла в прямом полете (Upright)
# vertical: Слот, куда можно поставить 1/4 или 3/4 бочки для ухода на ось Y
# horizontal: Слот, куда можно ставить только STAY_ROLLS, чтобы не сломать ориентацию
OPENAERO_DICTIONARY = [
    {"olan": "o",  "name": "Петля", "slots": [("top", "horizontal")]},
    {"olan": "m",  "name": "Immelmann (Полупетля вверх)", "slots": [("exit", "mandatory_flip")]},
    {"olan": "a",  "name": "Split-S (Переворот)", "slots": [("entry", "mandatory_flip")]},
    {"olan": "c",  "name": "Half Cuban", "slots": [("exit", "mandatory_flip")]},
    {"olan": "rc", "name": "Reverse Cuban", "slots": [("entry", "mandatory_flip")]},
    {"olan": "j",  "name": "Вираж 180", "slots": []},
    {"olan": "ta", "name": "Прямой колокол", "slots": [("entry", "vertical"), ("exit", "vertical")]},
    {"olan": "h",  "name": "Хаммерхед", "slots": [("entry", "vertical"), ("exit", "vertical")]},
    {"olan": "b",  "name": "Humpty Bump", "slots": [("entry", "vertical"), ("exit", "vertical")]},
    {"olan": "p",  "name": "P-Loop", "slots": [("entry", "vertical"), ("exit", "mandatory_flip")]},
    {"olan": "rp", "name": "Reverse P-Loop", "slots": [("entry", "mandatory_flip"), ("exit", "vertical")]},
    [cite_start]{"olan": "4jio2", "name": "Rolling Circle", "slots": []} # Берем легитимную связку из твоих файлов [cite: 45]
]

def get_roll(roll_type):
    if roll_type == "STAY": return random.choice(STAY_ROLLS)
    elif roll_type == "FLIP": return random.choice(FLIP_ROLLS)
    elif roll_type == "Y": return random.choice(Y_ROLLS)
    return ""

def build_bulletproof_sequence(length):
    sequence = []
    axis = 'X' # Всегда начинаем по главной оси
    
    for i in range(length):
        fig = random.choice(OPENAERO_DICTIONARY)
        
        # 1. Проверяем, нужны ли манипуляции с осью Y
        has_vertical = any(slot_type == "vertical" for _, slot_type in fig["slots"])
        need_axis_change = False
        
        if has_vertical:
            if axis == 'Y' and i >= length - 2:
                # Если скоро конец, принудительно возвращаемся на X
                need_axis_change = True
            elif axis == 'X' and random.random() < 0.2:
                need_axis_change = True
            elif axis == 'Y' and random.random() < 0.4:
                need_axis_change = True

        rolls = {"entry": "", "top": "", "exit": ""}
        axis_changed_this_fig = False
        
        # 2. Раздаем вращения строго по правилам слотов
        for slot_pos, slot_type in fig["slots"]:
            if slot_type == "mandatory_flip":
                rolls[slot_pos] = get_roll("FLIP")
            elif slot_type == "horizontal":
                if random.random() < 0.4:
                    rolls[slot_pos] = get_roll("STAY")
            elif slot_type == "vertical":
                # Если нужна смена оси, ставим 90/270 градусов на первую попавшуюся вертикаль
                if need_axis_change and not axis_changed_this_fig:
                    rolls[slot_pos] = get_roll("Y")
                    axis_changed_this_fig = True
                    axis = 'Y' if axis == 'X' else 'X'
                elif random.random() < 0.4:
                    rolls[slot_pos] = get_roll("STAY")
                    
        # 3. Собираем макрос
        macro = f"{rolls.get('entry', '')}{fig['olan']}{rolls.get('top', '')}{rolls.get('exit', '')}"
        sequence.append({"macro": macro, "desc": fig["name"], "axis": axis})
        
    # Failsafe: Если комплекс случайно закончился на оси Y, добавляем корректирующую фигуру
    if axis == 'Y':
        sequence.append({"macro": "1h", "desc": "Хаммерхед (Принудительный возврат на ось X)", "axis": 'X'})
        
    return sequence

# --- Streamlit UI ---
st.set_page_config(page_title="Unlimited OLAN PRO", page_icon="🛩️")
st.title("🏆 Валидный OLAN Генератор (U-to-U Logic)")
st.write("Скрипт использует строгую логику U-to-U (Upright to Upright), гарантируя обязательные полубочки для фигур, меняющих положение самолета.")

num_figs = st.sidebar.slider("Количество фигур", 5, 20, 10)

if st.button("Сгенерировать комплекс"):
    complex_data = build_bulletproof_sequence(num_figs)
    final_string = " ".join([fig["macro"] for fig in complex_data])
    
    st.success("✅ Готово! Скопируй строку, вставь в OpenAero и нажми кнопку **Separate figures**.")
    st.code(final_string, language="text")
    
    st.write("### Логика полета:")
    for i, fig in enumerate(complex_data):
        axis_icon = "🔵 X" if fig["axis"] == "X" else "🔴 Y"
        st.write(f"**{i+1}.** `{fig['macro']}` — {fig['desc']} *(Ось: {axis_icon})*")
