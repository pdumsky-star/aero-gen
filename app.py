import streamlit as st
import random
import json

# 1. Загрузка каталога фигур
def load_catalog():
    with open('catalog.json', 'r', encoding='utf-8') as f:
        return json.load(f)

# 2. Ручная сборка XML для 100% совместимости с форматом .seq
def generate_seq_xml_raw(sequence_data):
    # Формируем блоки фигур (теги <figure>)
    figs_xml = ""
    total_k = 0
    for i, fig in enumerate(sequence_data):
        # Базовый элемент фигуры [cite: 128, 173]
        elements_xml = f"""
            <element>
                <aresti>{fig['base_id']}</aresti>
                <k>{fig['base_k']}</k>
            </element>"""
        
        # Добавленные вращения (rolls) [cite: 132, 174]
        for r in fig["rolls"]:
            elements_xml += f"""
            <element>
                <aresti>{r['id']}</aresti>
                <k>{r['k']}</k>
            </element>"""
            
        figs_xml += f"""
        <figure>
            <nr>{i + 1}</nr>
            <sf>4</sf>{elements_xml}
            <figk>{fig['total_k']}</figk>
        </figure>"""
        total_k += fig['total_k']

    # Итоговый XML без декларации <?xml...?> [cite: 241]
    # Добавлены ключи rules=CIVA и category=Unlimited для автоматической отрисовки [cite: 81, 163]
    final_xml = f"""<sequence>
    <class>powered</class>
    <sequence_text></sequence_text>
    <oa_version>2024.1.1</oa_version>
    <default_view>B</default_view>
    <figures>{figs_xml}
        <figurek>{total_k}</figurek>
        <totalk>{total_k}</totalk>
    </figures>
    <settings xmlns="http://www.w3.org/1999/xhtml">
        <setting><key>language</key><value>en</value></setting>
        <setting><key>rules</key><value>CIVA</value></setting>
        <setting><key>category</key><value>Unlimited</value></setting>
        <setting><key>gridColumns</key><value>5</value></setting>
        <setting><key>showHandles</key><value>true</value></setting>
    </settings>
</sequence>"""
    return final_xml

# 3. Логика построения комплекса (движок генерации)
def build_complex(catalog, length):
    complex_data = []
    curr_pos, on_y = "U", False # U - upright, I - inverted
    
    for _ in range(length):
        # Фильтрация фигур по точке входа и текущей оси (X/Y)
        possible = [b for b in catalog["bases"] if b["in"] == curr_pos and (not on_y or b["y"])]
        
        if not possible: 
            curr_pos, on_y = "U", False # Сброс при тупике
            continue
            
        base = random.choice(possible)
        fig_rolls, fig_total_k = [], base["k"]
        
        # Добавляем вращения только на разрешенные типы линий [cite: 177, 182]
        for line in base["lines"]:
            if (random.random() < 0.8 and 
                line in catalog["rolls"] and 
                len(catalog["rolls"][line]) > 0): # Защита от IndexError
                
                roll = random.choice(catalog["rolls"][line])
                fig_rolls.append(roll)
                fig_total_k += roll["k"]
        
        complex_data.append({
            "base_id": base["id"], 
            "base_k": base["k"],
            "rolls": fig_rolls, 
            "total_k": fig_total_k
        })
        
        # Обновление состояния для следующей фигуры 
        curr_pos = base["out"]
        if base["y"]:
            on_y = not on_y
            
    return complex_data

# 4. Интерфейс Streamlit
st.set_page_config(page_title="Unlimited SEQ Gen", page_icon="✈️")
st.title("🏆 Unlimited .SEQ Generator")
st.write("Генератор тренировочных комплексов. Скачайте файл и перетащите его в OpenAero.")

try:
    catalog = load_catalog()
    num_figs = st.sidebar.slider("Количество фигур", 5, 20, 12)
    
    if st.button("Сгенерировать тренировку"):
        seq_data = build_complex(catalog, num_figs)
        xml_res = generate_seq_xml_raw(seq_data)
        
        st.success(f"Комплекс на {len(seq_data)} фигур готов!")
        
        st.download_button(
            label="📥 Скачать файл .seq",
            data=xml_res,
            file_name="Training_Unlimited.seq",
            mime="application/xml"
        )
        
        # Предпросмотр состава в интерфейсе
        for i, f in enumerate(seq_data):
            rolls_list = [r['id'] for r in f['rolls']]
            st.write(f"**{i+1}.** {f['base_id']} + {rolls_list} (K: {f['total_k']})")

except FileNotFoundError:
    st.error("Ошибка: Файл catalog.json не найден в корне проекта!")
except Exception as e:
    st.error(f"Произошла ошибка: {e}")
