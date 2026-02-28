import streamlit as st
import random
import urllib.parse
import json

def load_catalog():
    with open('catalog.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_unlimited(catalog, length):
    seq = []
    curr_pos = "U" # U - Upright, I - Inverted
    on_y = False
    
    attempts = 0
    while len(seq) < length and attempts < 100:
        attempts += 1
        possible = [
            b for b in catalog["bases"] 
            if b["in"] == curr_pos and (not on_y or b["y"])
        ]
        
        if not possible:
            # Аварийный выход: сброс на прямую линию
            curr_pos = "U"
            on_y = False
            continue
            
        base = random.choice(possible)
        fig_id = base["id"]
        
        # Добавляем вращение (80% шанс для Unlimited)
        if random.random() < 0.8:
            roll = random.choice(catalog["rolls"])
            fig_id = f"{fig_id}({roll['id']})"
            
        seq.append({"id": fig_id, "desc": base["desc"]})
        curr_pos = base["out"]
        if base["y"]: on_y = not on_y
            
    return seq

st.set_page_config(page_title="Unlimited Gen PRO", page_icon="✈️")
st.title("🏆 Unlimited Aero Generator")

try:
    catalog = load_catalog()
    count = st.sidebar.slider("Фигур в комплексе", 5, 15, 10)

    if st.button("Сгенерировать тренировку"):
        sequence = generate_unlimited(catalog, count)
        olan_str = ",".join([f["id"] for f in sequence])
        
        # Ссылка для OpenAero
        link = f"https://openaero.net/?olan={urllib.parse.quote(olan_str)}"
        
        st.success("Комплекс готов!")
        st.link_button("🔥 ОТКРЫТЬ В OPENAERO", link)
        
        st.write("### Состав:")
        for idx, f in enumerate(sequence):
            st.write(f"**{idx+1}.** {f['id']} — {f['desc']}")

except FileNotFoundError:
    st.error("Файл catalog.json не найден в папке с приложением!")
