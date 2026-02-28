import streamlit as st
import random
import urllib.parse
import json

def load_catalog():
    with open('catalog.json', 'r') as f:
        return json.load(f)

def generate_unlimited_sequence(catalog, length):
    seq = []
    current_pos = "U" # U - Upright, I - Inverted
    on_y_axis = False
    
    for _ in range(length):
        # Логика выбора:
        # 1. Если мы на оси Y, ищем фигуры с y=true (они возвращают на X)
        # 2. Вход (in) должен соответствовать текущему положению (current_pos)
        possible = [
            b for b in catalog["bases"]
            if b["in"] == current_pos and (on_y_axis == b["y"] or b["y"] == True)
        ]
        
        if not possible: break
        
        base = random.choice(possible)
        fig_id = base["id"]
        total_k = base["k"]
        
        # Добавляем вращение для Unlimited (шанс 70%)
        if random.random() < 0.7:
            roll = random.choice(catalog["rolls"])
            fig_id = f"{fig_id}({roll['id']})"
            total_k += roll["k"]
            
        seq.append({"id": fig_id, "k": total_k, "desc": base["desc"]})
        
        # Обновляем состояние
        current_pos = base["out"]
        if base["y"]:
            on_y_axis = not on_y_axis
            
    return seq

# Интерфейс
st.title("🛩️ CIVA Unlimited Generator")

try:
    catalog = load_catalog()
    count = st.sidebar.slider("Фигур в комплексе", 5, 15, 10)
    
    if st.button("Сгенерировать комплекс"):
        sequence = generate_unlimited_sequence(catalog, count)
        
        olan_string = ",".join([f["id"] for f in sequence])
        link = f"https://openaero.net/#olan={urllib.parse.quote(olan_string)}"
        
        st.success(f"Комплекс из {len(sequence)} фигур готов!")
        st.link_button("Открыть в OpenAero ↗️", link)
        
        for idx, f in enumerate(sequence):
            st.write(f"**{idx+1}.** {f['id']} — {f['desc']} (K: {f['k']})")
            
except FileNotFoundError:
    st.error("Ошибка: Создайте файл catalog.json в репозитории!")
