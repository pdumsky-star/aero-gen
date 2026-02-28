import streamlit as st
import random
import json
import xml.etree.ElementTree as ET

# Загрузка каталога (оставляем без изменений)
def load_catalog():
    with open('catalog.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_seq_xml(sequence_data):
    """Генерирует XML без декларации и лишних пробелов для 100% совместимости"""
    root = ET.Element("sequence")
    ET.SubElement(root, "class").text = "powered"
    ET.SubElement(root, "sequence_text").text = "" # Обязательно для парсера OpenAero
    ET.SubElement(root, "oa_version").text = "2024.1.1"
    ET.SubElement(root, "default_view").text = "B"
    
    figures_ele = ET.SubElement(root, "figures")
    total_k = 0
    
    for i, fig in enumerate(sequence_data):
        figure = ET.SubElement(figures_ele, "figure")
        ET.SubElement(figure, "nr").text = str(i + 1)
        ET.SubElement(figure, "sf").text = "4"
        
        # Базовая фигура
        el_base = ET.SubElement(figure, "element")
        ET.SubElement(el_base, "aresti").text = str(fig["base_id"])
        ET.SubElement(el_base, "k").text = str(fig["base_k"])
        
        # Вращения
        for r in fig["rolls"]:
            el_roll = ET.SubElement(figure, "element")
            ET.SubElement(el_roll, "aresti").text = str(r["id"])
            ET.SubElement(el_roll, "k").text = str(r["k"])
        
        ET.SubElement(figure, "figk").text = str(fig["total_k"])
        total_k += fig["total_k"]
    
    ET.SubElement(figures_ele, "figurek").text = str(total_k)
    ET.SubElement(figures_ele, "totalk").text = str(total_k)
    
    # Настройки с пространством имен как в оригинале
    settings = ET.SubElement(root, "settings", {"xmlns": "http://www.w3.org/1999/xhtml"})
    for k, v in [("language", "en"), ("gridColumns", "5"), ("showHandles", "true")]:
        s = ET.SubElement(settings, "setting")
        ET.SubElement(s, "key").text = k
        ET.SubElement(s, "value").text = v

    # Генерируем строку БЕЗ <?xml ... ?>
    return ET.tostring(root, encoding='utf-8', method='xml').decode('utf-8')

# Логика сборки комплекса (оставляем без изменений)
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

# Streamlit UI
st.title("🏆 Unlimited .SEQ Generator")

try:
    catalog = load_catalog()
    num_figs = st.sidebar.slider("Фигур", 5, 20, 12)
    
    if st.button("Сгенерировать .seq"):
        seq_data = build_complex(catalog, num_figs)
        xml_res = generate_seq_xml(seq_data)
        
        st.download_button(
            label="📥 Скачать файл .seq",
            data=xml_res,
            file_name="Training_Unlimited.seq",
            mime="application/xml"
        )
except FileNotFoundError:
    st.error("catalog.json не найден!")
