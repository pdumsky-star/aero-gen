import streamlit as st
import random
import json

def load_catalog():
    with open('catalog.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def build_complex(catalog, length):
    complex_data = []
    curr_pos, on_y = "U", False 
    
    for _ in range(length):
        possible = [b for b in catalog["bases"] if b["in"] == curr_pos and (not on_y or b["y"])]
        if not possible: 
            curr_pos, on_y = "U", False
            continue
            
        base = random.choice(possible)
        fig_rolls, fig_total_k = [], base["k"]
        
        for line in base["lines"]:
            if (random.random() < 0.8 and 
                line in catalog["rolls"] and 
                len(catalog["rolls"][line]) > 0):
                
                roll = random.choice(catalog["rolls"][line])
                fig_rolls.append(roll)
                fig_total_k += roll["k"]
        
        complex_data.append({
            "base_id": base["id"], 
            "rolls": [r["id"] for r in fig_rolls], 
            "total_k": fig_total_k
        })
        
        curr_pos = base["out"]
        if base["y"]:
            on_y = not on_y
            
    return complex_data

def generate_shorthand_string(seq_data):
    """Превращает массив фигур в строку для вставки в OpenAero"""
    parts = []
    for fig in seq_data:
        parts.append(fig["base_id"])
        # Добавляем вращения сразу после базовой фигуры
        parts.extend(fig["rolls"])
    return " ".join(parts)

st.set_page_config(page_title="Unlimited Gen", page_icon="✈️")
st.title("🏆 Unlimited Sequence Generator")
st.write("Сгенерируйте комплекс, скопируйте строку и вставьте её в верхнее текстовое поле в OpenAero.")

try:
    catalog = load_catalog()
    num_figs = st.sidebar.slider("Количество фигур", 5, 20, 10)
    
    if st.button("Сгенерировать комплекс"):
        seq_data = build_complex(catalog, num_figs)
        shorthand_str = generate_shorthand_string(seq_data)
        
        st.success("Готово! Скопируйте строку ниже:")
        # Выводим строку в удобном поле для копирования
        st.code(shorthand_str, language="text")
        
        st.write("### Детализация:")
        total_k = sum(f["total_k"] for f in seq_data)
        for i, f in enumerate(seq_data):
            st.write(f"**{i+1}.** {f['base_id']} {' '.join(f['rolls'])}")
        st.write(f"**Суммарный K-фактор:** {total_k}")

except FileNotFoundError:
    st.error("Ошибка: Файл catalog.json не найден!")
