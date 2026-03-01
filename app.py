import streamlit as st
import random

# Точная база соответствий Арести -> OLAN для OpenAero
# slots определяют, куда можно "повесить" вращение: 'entry' (до фигуры), 'top' (в вершине), 'exit' (после)
OPENAERO_DICTIONARY = [
    {"aresti": "7.4.1.1", "olan": "o",  "name": "Петля", "slots": ["top"]},
    {"aresti": "7.2.2.1", "olan": "m",  "name": "Полупетля вверх (Immelmann)", "slots": ["exit"]},
    {"aresti": "7.2.3.3", "olan": "a",  "name": "Переворот (Split-S)", "slots": ["entry"]},
    {"aresti": "8.5.2.1", "olan": "rc", "name": "Reverse Cuban", "slots": ["entry", "exit"]},
    {"aresti": "8.5.6.1", "olan": "c",  "name": "Cuban 8", "slots": ["entry", "exit"]},
    {"aresti": "2.2.1.1", "olan": "j",  "name": "Вираж 180", "slots": []},
    {"aresti": "6.2.1.1", "olan": "ta", "name": "Прямой колокол (Tail Slide)", "slots": ["entry", "exit"]},
    {"aresti": "5.2.1.1", "olan": "h",  "name": "Хаммерхед", "slots": ["entry", "exit"]},
    {"aresti": "8.4.1.1", "olan": "b",  "name": "Humpty Bump", "slots": ["entry", "top", "exit"]},
    {"aresti": "8.6.8.1", "olan": "p",  "name": "P-Loop", "slots": ["entry", "exit"]},
    {"aresti": "8.6.2.1", "olan": "rp", "name": "Reverse P-Loop", "slots": ["entry", "exit"]},
    {"aresti": "2.4.4.1", "olan": "4jio2", "name": "Rolling Circle (1 круг, 4 бочки)", "slots": []}
]

# Вращения в формате OLAN
OLAN_ROLLS = ["2", "4", "8", "24", "44", "34", "3f", "if", "f"]

def generate_olan_roll():
    """Генерация вращения со сменой направления (например: 2,44)"""
    roll = random.choice(OLAN_ROLLS)
    # 30% вероятность комбинированного вращения со сменой направления
    if random.random() < 0.3:
        second_roll = random.choice(OLAN_ROLLS)
        return f"{roll},{second_roll}"
    return roll

def build_complex(length):
    sequence = []
    
    for _ in range(length):
        base = random.choice(OPENAERO_DICTIONARY)
        
        entry_roll = ""
        top_roll = ""
        exit_roll = ""
        
        # Развешиваем бочки по доступным линиям
        if base["slots"]:
            for slot in base["slots"]:
                if random.random() < 0.5: # 50% шанс поставить бочку на линию
                    roll = generate_olan_roll()
                    if slot == "entry": entry_roll = roll
                    if slot == "top": top_roll = roll
                    if slot == "exit": exit_roll = roll
        
        # Сборка OLAN-макроса (Строго: Входная_бочка + База + Верхняя_бочка + Выходная_бочка)
        # Пример: "24" + "a" + "" + "3f" = 24a3f
        macro = f"{entry_roll}{base['olan']}{top_roll}{exit_roll}"
        
        sequence.append({
            "macro": macro,
            "desc": base["name"]
        })
        
    return sequence

st.set_page_config(page_title="OpenAero OLAN Gen", page_icon="✈️")
st.title("🏆 Нативный OLAN Генератор")
st.write("Генерирует чистый макро-код, понятный движку OpenAero без необходимости настраивать правила CIVA.")

num_figs = st.sidebar.slider("Количество фигур", 5, 15, 10)

if st.button("Сгенерировать комплекс"):
    complex_data = build_complex(num_figs)
    
    # Склеиваем макросы пробелом (для новых фигур) и добавляем случайные отступы по сетке (например, (0,5))
    final_parts = []
    for i, fig in enumerate(complex_data):
        final_parts.append(fig["macro"])
        # Каждые 4 фигуры добавляем переход на новую строку для красивой отрисовки
        if (i + 1) % 4 == 0 and i != len(complex_data) - 1:
            final_parts.append("(0,12)") 
            
    final_string = " ".join(final_parts)
    
    st.success("✅ Готово! Скопируй строку и вставь в верхнее поле OpenAero.")
    st.code(final_string, language="text")
    
    st.write("### Состав комплекса:")
    for i, fig in enumerate(complex_data):
        st.write(f"**{i+1}.** `{fig['macro']}` — {fig['desc']}")
except FileNotFoundError:
    st.error("Ошибка: Файл catalog.json не найден!")
