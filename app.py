import streamlit as st
import random
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

def load_catalog():
    with open('catalog.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_seq_xml(sequence_data):
    """Формирует XML структуру формата .seq на основе ваших файлов"""
    root = ET.Element("sequence")
    ET.SubElement(root, "class").text = "powered"
    
    figures_ele = ET.SubElement(root, "figures")
    total_k = 0
    
    for i, fig in enumerate(sequence_data):
        figure = ET.SubElement(figures_ele, "figure")
        ET.SubElement(figure, "nr").text = str(i + 1)
        ET.SubElement(figure, "sf").text = "4" # Стандартный тип секции
        
        # Базовая фигура
        el_base = ET.SubElement(figure, "element")
        ET.SubElement(el_base, "aresti").text = fig["base_id"]
        ET.SubElement(el_base, "k").text = str(fig["base_k"])
        
        # Вращения
        for r in fig["rolls"]:
            el_roll = ET.SubElement(figure, "element")
            ET.SubElement(el_roll, "aresti").text = r["id"]
            ET.SubElement(el_roll, "k").text = str(r["k"])
        
        ET.SubElement(figure, "figk").text = str(fig["total_k"])
        total_k += fig["total_k"]
    
    ET.SubElement(figures_ele, "figurek").text = str(total_k)
    ET.SubElement(figures_ele, "totalk").text = str(total_k)
    
    # Системные настройки (как в ваших примерах)
    settings = ET.SubElement(root, "settings")
    for key, val in [("language", "en"), ("gridColumns", "5"), ("showHandles", "true")]:
        s = ET.SubElement(settings, "setting")
        ET.SubElement(s, "key").text = key
        ET.SubElement(s, "value").text = val

    # Красивое форматирование XML
    xml_str = ET.tostring(root, encoding='utf-8')
    return minidom.parseString(xml_str).toprettyxml(indent="    ")

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
        
        # Добавляем вращения только на разрешенные линии
        for line in base["lines"]:
            if random.random() < 0.8 and line in catalog["rolls"] and catalog["rolls"][line]:
                roll = random.choice(catalog["rolls"][line])
                fig_rolls.append(roll)
                fig_total_k += roll["k"]
        
        complex_data.append({
            "base_id": base["id"], "base_k": base["k"],
            "rolls": fig_rolls, "total_k": fig_total_k
        })
        curr_pos, on_y = base["out"], (not on_y if base["y"] else on_y)
            
    return complex_data

# Streamlit Интерфейс
st.set_page_config(page_title="Unlimited SEQ Gen", page_icon="✈️")
st.title("🏆 Unlimited .SEQ Generator")

try:
    catalog = load_catalog()
    num_figs = st.sidebar.slider("Количество фигур", 5, 20, 12)
    
    if st.button("Сгенерировать тренировку"):
        seq_data = build_complex(catalog, num_figs)
        xml_res = generate_seq_xml(seq_data)
        
        st.success(f"Сгенерирован комплекс на {len(seq_data)} фигур!")
        st.download_button(
            label="📥 Скачать файл .seq",
            data=xml_res,
            file_name="Training_Unlimited.seq",
            mime="application/xml"
        )
        
        for i, f in enumerate(seq_data):
            rolls_str = ", ".join([r['id'] for r in f['rolls']])
            st.write(f"**{i+1}.** {f['base_id']} + [{rolls_str}] (K: {f['total_k']})")

except FileNotFoundError:
    st.error("Ошибка: Положите catalog.json в папку со скриптом!")
