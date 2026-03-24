import streamlit as st
import random

# ==========================================
# 1. БИБЛИОТЕКА ШАБЛОНОВ (БАЗОВЫЕ ФОРМЫ)
# ==========================================
# req_speed: Требуемая скорость для входа
# out_speed: Скорость, которая останется на выходе
# flip: Переворачивает ли "голая" фигура самолет на спину?
TEMPLATES = [
    # --- Горизонтальные фигуры (Вход: любой, Выход: Крейсер) ---
    {"macro": "2", "req_speed": ["HS", "MS"], "out_speed": "MS", "flip": False, "k": 8, "rolls": [""]},  # Горизонтальная бочка
    {"macro": "4", "req_speed": ["HS", "MS"], "out_speed": "MS", "flip": True, "k": 4, "rolls": [""]},   # Горизонтальная полубочка
    
    # --- Восходящие фигуры (Гасят скорость: Вход HS -> Выход LS) ---
    {"macro": "m{roll}", "req_speed": ["HS"], "out_speed": "LS", "flip": True, "k": 6, "rolls": ["", "4", "2"]},   # Иммельман
    {"macro": "v8{roll}", "req_speed": ["HS"], "out_speed": "LS", "flip": False, "k": 5, "rolls": ["", "4"]},      # Линия 45° вверх
    
    # --- Нисходящие фигуры (Дают разгон: Вход LS/MS -> Выход HS) ---
    {"macro": "a{roll}", "req_speed": ["LS", "MS"], "out_speed": "HS", "flip": True, "k": 6, "rolls": ["", "4", "2"]}, # Сплит-С
    {"macro": "d8{roll}", "req_speed": ["LS", "MS"], "out_speed": "HS", "flip": False, "k": 5, "rolls": ["", "4"]},    # Линия 45° вниз
    
    # --- Высокоэнергетические фигуры (Требуют разгон и сохраняют его) ---
    {"macro": "o", "req_speed": ["HS"], "out_speed": "HS", "flip": False, "k": 10, "rolls": [""]},                    # Петля
    {"macro": "c{roll}", "req_speed": ["HS"], "out_speed": "HS", "flip": True, "k": 14, "rolls": ["", "4", "2"]},     # Полукубанка
    {"macro": "rc{roll}", "req_speed": ["HS"], "out_speed": "HS", "flip": True, "k": 14, "rolls": ["", "4", "2"]},    # Реверс-кубанка
    {"macro": "b{roll}", "req_speed": ["HS"], "out_speed": "HS", "flip": False, "k": 13, "rolls": ["", "iv4"]},       # Хумпти-Бамп
    {"macro": "h{roll}", "req_speed": ["HS"], "out_speed": "HS", "flip": False, "k": 17, "rolls": ["", "iv4"]},       # Хаммерхед
]

# ==========================================
# 2. БИБЛИОТЕКА МОДИФИКАТОРОВ (ВРАЩЕНИЯ CIVA)
# ==========================================
ROLLS = {
    "": {"macro": "", "flip": False, "k": 0},        # Без вращения
    "4": {"macro": "4", "flip": True, "k": 4},       # Полубочка (переворачивает)
    "2": {"macro": "2", "flip": False, "k": 8},      # Полная бочка (не переворачивает)
    "iv4": {"macro": "iv4", "flip": True, "k": 3},   # Полубочка на вертикали вниз
}

# ==========================================
# 3. ЗАЩИТА ОСЕЙ (АППАРАТНЫЙ ВОЗВРАТ)
# ==========================================
def get_y_recovery_figure(current_speed):
    # Если мы на оси Y, нам нужно безопасно вернуться на главную ось X
    if current_speed == 'LS':
        # Со сваливания нельзя крутить вираж. Сначала ныряем (Сплит-С без бочек), набираем скорость
        return {"macro": "a", "out_speed": "HS", "flip": True, "k_factor": 6, "axis_change": False}
    else:
        # Из скорости крутим легитимный вираж на 90 градусов (возврат на X)
        return {"macro": "1j", "out_speed": "MS", "flip": False, "k_factor": 3, "axis_change": True}

# ==========================================
# 4. ДИНАМИЧЕСКИЙ ГЕНЕРАТОР КОМПЛЕКСОВ
# ==========================================
def build_tournament_sequence(num_hard, num_link, max_k_total, link_threshold):
    length = num_hard + num_link
    sequence = []
    
    # Стартовые условия: Летим прямо, Крейсерская скорость, Главная ось
    current_att = "U"     
    current_speed = "MS"  
    current_axis = "X"    
    
    current_k = 0
    hard_count = 0
    link_count = 0
    cons_hard = 0

    for i in range(length):
        # 1. Если самолет улетел на ось Y — принудительно спасаем его
        if current_axis == "Y":
            fig = get_y_recovery_figure(current_speed)
            sequence.append({
                "macro": fig["macro"], "speed_in": current_speed, "att_in": current_att, 
                "att_out": "I" if (current_att == "U" and fig["flip"]) or (current_att == "I" and not fig["flip"]) else "U", 
                "axis": "Y", "k_factor": fig["k_factor"]
            })
            current_att = sequence[-1]["att_out"]
            current_speed = fig["out_speed"]
            if fig["axis_change"]: current_axis = "X"
            current_k += fig["k_factor"]
            continue

        # 2. Иногда специально уходим на ось Y для турнирной красоты (через вираж)
        if current_speed in ["MS", "HS"] and random.random() < 0.15 and i < length - 2:
            sequence.append({
                "macro": "1j", "speed_in": current_speed, "att_in": current_att, 
                "att_out": current_att, "axis": "X->Y", "k_factor": 3
            })
            current_axis = "Y"
            current_speed = "MS"
            current_k += 3
            continue

        # 3. Фильтруем шаблоны по строгим правилам энергий
        valid_templates = [t for t in TEMPLATES if current_speed in t["req_speed"]]

        # 4. Менеджер бюджета (Сложные vs Простые)
        hard_templates = [t for t in valid_templates if t["k"] > link_threshold]
        link_templates = [t for t in valid_templates if t["k"] <= link_threshold]
        
        force_link = False
        if cons_hard >= 3 or hard_count >= num_hard: force_link = True
        
        pool_to_use = valid_templates
        if force_link and link_templates: pool_to_use = link_templates
        elif hard_templates and link_templates:
            pool_to_use = hard_templates if random.random() < 0.75 else link_templates

        if not pool_to_use:
            pool_to_use = valid_templates # Защита от тупика

        # 5. ДИНАМИЧЕСКИЙ СИНТЕЗ ФИГУРЫ (Шаблон + Модификатор)
        template = random.choice(pool_to_use)
        roll_key = random.choice(template["rolls"])
        roll_data = ROLLS[roll_key]

        # Собираем макрос (например: "c" + "4" = "c4")
        final_macro = template["macro"].format(roll=roll_data["macro"])
        
        # Складываем физику (Математика переворотов)
        total_flip = template["flip"] ^ roll_data["flip"]
        final_att = "I" if (current_att == "U" and total_flip) or (current_att == "I" and not total_flip) else "U"
        final_k = template["k"] + roll_data["k"]

        sequence.append({
            "macro": final_macro, "speed_in": current_speed, "att_in": current_att, 
            "att_out": final_att, "req_speed": template["req_speed"], "axis": "X", "k_factor": final_k
        })

        # Обновляем состояние самолета для следующей фигуры
        current_att = final_att
        current_speed = template["out_speed"]
        current_k += final_k
        
        if final_k > link_threshold:
            hard_count += 1; cons_hard += 1
        else:
            link_count += 1; cons_hard = 0

    return sequence, current_k

# --- Streamlit UI ---
st.set_page_config(page_title="Unlimited World Champ", page_icon="🏆", layout="wide")
st.title("🏆 Unlimited Pro (Dynamic Assembly Engine)")
st.write("Генератор собирает фигуры прямо на лету! Он берет базовые шаблоны (петли, кубанки) и динамически навешивает на них разрешенные CIVA бочки, математически вычисляя перевороты.")

st.sidebar.header("🛠 Бюджет CIVA")
num_hard = st.sidebar.slider("Боевые фигуры (Сложные)", 5, 12, 10)
num_link = st.sidebar.slider("Связочные фигуры (Простые)", 2, 6, 4)
max_k_total = st.sidebar.slider("Лимит сложности (Max Total K)", 300, 500, 420)
link_threshold = st.sidebar.slider("Порог K-фактора (Связочная <= K)", 10, 35, 25)

if st.button("Сгенерировать комплекс"):
    complex_data, total_k = build_tournament_sequence(num_hard, num_link, max_k_total, link_threshold)
    
    # OpenAero нужен "+" в самом начале, чтобы задать стартовое положение
    final_string = "+ " + " ".join([fig["macro"] for fig in complex_data])
    
    st.success(f"✅ Готово! Итоговый K-Фактор: **{total_k}K**")
    st.code(final_string, language="text")
    
    st.write("### Телеметрия:")
    for i, fig in enumerate(complex_data):
        att_in = "⬆️ Прямо" if fig["att_in"] == "U" else "⬇️ Спина"
        spd_icon = "🛑 Stall (LS)" if fig["speed_in"] == "LS" else ("🔥 Fast (HS)" if fig["speed_in"] == "HS" else "💨 Cruise (MS)")
        type_icon = "⚔️ **Боевая**" if fig["k_factor"] > link_threshold else "🔗 *Связочная*"
        
        st.write(f"**{i+1}.** `{fig['macro']}` | **[{fig['k_factor']}K]** {type_icon}")
        st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;Вход: {att_in} ({spd_icon}) | Выход: {'⬆️ Прямо' if fig['att_out'] == 'U' else '⬇️ Спина'} | Ось: {fig.get('axis', 'X')}")
