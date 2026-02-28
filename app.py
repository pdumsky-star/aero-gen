import streamlit as st
import random
import json

def load_catalog():
    with open('catalog.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_seq_xml_raw(sequence_data):
    """Ручная сборка XML для 100% идентичности с оригиналами OpenAero"""
    
    # Формируем блоки фигур
    figs_xml = ""
    total_k = 0
    for i, fig in enumerate(sequence_data):
        elements_xml = f"""
            <element>
                <aresti>{fig['base_id']}</aresti>
                <k>{fig['base_k']}</k>
            </element>"""
        
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

    # Собираем итоговый файл (без <?xml...?> и с правильными отступами)
    # Структура основана на [cite: 1, 35, 219]
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
        <setting>
            <key>language</key>
            <value>en</value>
        </setting>
        <setting>
            <key>gridColumns</key>
            <value>5</value>
        </setting>
        <setting>
            <key>showHandles</key>
            <value>true</value>
        </setting>
    </settings>
</sequence>"""
    return final_xml

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
            # Проверяем: 1. Нужен ли ролл, 2. Есть ли такой тип линии, 3. НЕ ПУСТОЙ ли список роллов
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
        curr_pos, on_y = base["out"], (not on_y if base["y"] else on_y)
    return complex_data

# Streamlit UI
st.title("✈️ Unlimited .SEQ Generator PRO")

try:
    catalog = load_catalog()
    num_figs = st.sidebar.slider("Количество фигур", 5, 15, 12)
    
    if st.button("Сгенерировать .seq"):
        seq_data = build_complex(catalog, num_figs)
        xml_res = generate_seq_xml_raw(seq_data)
        
        st.download_button(
            label="📥 Скачать файл .seq",
            data=xml_res,
            file_name="Training_Unlimited.seq",
            mime="application/xml"
        )
        st.success("Файл готов! Просто перетащите его в OpenAero.")
except FileNotFoundError:
    st.error("catalog.json не найден!")
