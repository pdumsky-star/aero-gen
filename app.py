import streamlit as st
import random
import json

# ==========================================
# DATA-DRIVEN ДВИЖОК
# ==========================================
def load_database():
    try:
        with open('civa_database.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("❌ Файл civa_database.json не найден! Положите файлы .seq в папку и запустите parser.py")
        st.stop()

DATABASE = load_database()

def build_data_driven_sequence(length):
    sequence = []
    # Доступные семейства фигур, которые мы смогли вытащить из файлов
    available_families = list(DATABASE.keys())
    
    for _ in range(length):
        # Выбираем случайное семейство фигур
        family = random.choice(available_families)
        # Берем 100% рабочий, доказанный макрос из этого семейства
        fig_data = random.choice(DATABASE[family])
        
        sequence.append({
            "macro": fig_data["macro"],
            "aresti": ", ".join(fig_data["aresti"])
        })
        
    return sequence

# --- Streamlit UI ---
st.set_page_config(page_title="Aero Gen Pro", page_icon="🛩️")
st.title("🏆 Data-Driven Генератор")
st.write("Комплекс собирается исключительно из легитимных связок, извлеченных из реальных соревновательных файлов.")

num_figs = st.sidebar.slider("Количество фигур", 5, 20, 10)

if st.button("Сгенерировать комплекс"):
    complex_data = build_data_driven_sequence(num_figs)
    final_string = " ".join([fig["macro"] for fig in complex_data])
    
    st.success("✅ Готово! Копируй строку, вставляй в OpenAero и нажимай **Separate figures**.")
    st.code(final_string, language="text")
    
    st.write("### Детализация (Из каких реальных фигур это собрано):")
    for i, fig in enumerate(complex_data):
        st.write(f"**{i+1}.** `{fig['macro']}` *(Каталог Арести: {fig['aresti']})*")
