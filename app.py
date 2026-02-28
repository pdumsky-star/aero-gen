import streamlit as st
import random
import urllib.parse

# Упрощенная база данных фигур (на старте внесем сюда основные элементы Unlimited)
# В полной версии мы вынесем это в отдельный json
CATALOG = {
    "bases": [
        {"id": "1.1.1.1", "k": 2, "in": "U", "out": "U", "y": False, "name": "Line"},
        {"id": "7.4.1.1", "k": 14, "in": "U", "out": "I", "y": False, "name": "Half Cuban"},
        {"id": "8.4.1.1", "k": 11, "in": "U", "out": "U", "y": False, "name": "Humpty Bump"},
        {"id": "5.2.1.1", "k": 17, "in": "U", "out": "U", "y": False, "name": "Stall Turn"},
        {"id": "8.5.2.1", "k": 20, "in": "U", "out": "U", "y": True, "name": "Half Cuban to Y"},
        {"id": "2.1.1.1", "k": 12, "in": "U", "out": "U", "y": False, "name": "Rolling Circle (90 deg)"}
    ],
    "rolls": [
        {"id": "9.1.1.1", "k": 6, "name": "Slow Roll"},
        {"id": "9.11.1.1", "k": 15, "name": "Snap Roll"},
        {"id": "9.4.3.4", "k": 11, "name": "4-point Roll"}
    ]
}

def generate_sequence(length):
    seq = []
    current_pos = "U" # Upright
    on_y_axis = False
    
    for i in range(length):
        # Фильтруем фигуры: вход должен совпадать с выходом предыдущей
        # И если мы на оси Y, следующая фигура должна вернуть нас на X
        possible = [
            f for f in CATALOG["bases"] 
            if f["in"] == current_pos and (not on_y_axis or f["y"])
        ]
        
        if not possible: break # Предохранитель
        
        fig = random.choice(possible).copy()
        
        # Для Unlimited добавляем вращение (Family 9)
        if random.random() > 0.4:
            roll = random.choice(CATALOG["rolls"])
            fig["id"] = f"{fig['id']}({roll['id']})"
            fig["k"] += roll["k"]
            
        seq.append(fig)
        current_pos = fig["out"]
        # Если фигура меняет ось, переключаем флаг
        if fig["y"]:
            on_y_axis = not on_y_axis
            
    return seq

# Интерфейс Streamlit
st.set_page_config(page_title="Unlimited Aero Gen", page_icon="✈️")
st.title("✈️ Unlimited Aerobatic Generator")
st.write("Генератор тренировочных комплексов для категории Unlimited.")

count = st.slider("Количество фигур в комплексе", 5, 20, 10)

if st.button("Сгенерировать новый комплекс"):
    sequence = generate_sequence(count)
    
    # Собираем OLAN строку
    olan_parts = [f["id"] for f in sequence]
    olan_string = ",".join(olan_parts)
    
    # Ссылка на OpenAero
    link = f"https://openaero.net/#olan={urllib.parse.quote(olan_string)}"
    
    st.subheader("Ваш комплекс:")
    for idx, f in enumerate(sequence):
        st.write(f"{idx+1}. {f['id']} (K: {f['k']})")
    
    st.link_button("🚀 Открыть в OpenAero (Визуализировать)", link)

st.info("Это MVP. Логика будет дополняться правилами CIVA.")
