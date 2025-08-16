import streamlit as st

# 状態を初期化
if "is_on" not in st.session_state:
    st.session_state.is_on = False

def toggle_state():
    st.session_state.is_on = not st.session_state.is_on

# 現在の状態に応じた画像を選択
img_on = "images/test001-l.bmp"   # クリック時のON画像
img_off = "images/test001-r.bmp"  # クリック時のOFF画像
current_img = img_on if st.session_state.is_on else img_off

# 画像をボタン風に表示
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("", key="toggle_button"):
        toggle_state()
    st.image(current_img, use_container_width =True)