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
        # Базовый элемент фигуры
        elements_xml = f"""
            <element>
                <aresti>{fig['base_id']}</aresti>
                <k>{fig['base_k']}</k>
            </element>"""
        
        # Добавленные вращения (rolls)
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

    # Итоговый XML без декларации <?xml...?> для предотвращения ошибок импорта
    # Добавлены ключи rules=CIVA и category=Unlimited для автоматической отрисовки
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
        possible = [b for b in catalog["bases"] if b["in"] == curr_
