
from email.policy import default
import os
import numpy as np
import re
import cv2
import time
import streamlit as st
import flip_evaluator as flip
from streamlit_image_comparison import image_comparison
from datetime import datetime, timedelta
from collections import defaultdict

directory = './images'

error_threshold = 0.01

image_width = 800

class ImageObject:
    def __init__(self, date_obj: datetime = None, filepath: str = None) -> None:
        self.date_obj = date_obj
        self.filepath = filepath
        self.image = None
    
    def get_fullpath(self):
        return directory + '/' + self.filepath

    def load_image(self):
        fullpath = self.get_fullpath()
        img = cv2.imread(fullpath)
        self.image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.image = np.asarray(self.image)

class Item:
    def __init__(self) -> None:
        self.error = None
        self.error_map = None
        self.images = []


# 状態を初期化
if "current_image" not in st.session_state:
    st.session_state.current_image = None

if "items_by_name" not in st.session_state:
    st.session_state.items_by_name = {}
    pattern = re.compile(r"^(?P<name>.+)-(?P<date>\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})\.bmp$")
    
    for fname in os.listdir(directory):
        match = pattern.match(fname)
        if match:
            name = match.group("name")
            
            if name not in st.session_state.items_by_name:
                st.session_state.items_by_name[name] = Item()

            date_str = match.group("date")
            d = datetime.strptime(date_str, "%Y-%m-%d-%H-%M-%S")
            
            st.session_state.items_by_name[name].images.append(ImageObject(date_obj = d, filepath = fname))
            
    for name, item in st.session_state.items_by_name.items():
        # 日付でソート
        item.images.sort(key=lambda x: x.date_obj, reverse=True)  
        # 最新2イメージのみロード
        item.images[0].load_image()
        item.images[1].load_image()
        flipErrorMap, meanFLIPError, parameters = flip.evaluate(item.images[0].get_fullpath(), item.images[1].get_fullpath(), "LDR")
        item.error = meanFLIPError
        item.error_map = flipErrorMap
        
    
# ページ設定（全幅レイアウト）
st.set_page_config(layout="wide")

# カスタムCSSでパディングをなくす
st.markdown("""
    <style>
    .block-container {
        padding-top: 0rem;
        padding-bottom: 0rem;
        padding-left: 0rem;
        padding-right: 0rem;
    }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    
    st.header("Rendering Test")

    option = st.selectbox(
    "Sort Method",
    ("Name", "Error", "Date / New", "Date / Old"))
    
    filter_text = st.text_input(
    "Filter")
    
    if option == 'Name':
        sorted_list = sorted(st.session_state.items_by_name.items(), key=lambda x: x[0])
    elif option == 'Error':
        sorted_list = sorted(st.session_state.items_by_name.items(), key=lambda x: x[1].error)
    elif option == 'Date / New':
        sorted_list = sorted(st.session_state.items_by_name.items(), key=lambda x: x[1].images[0].date_obj, reverse=True)
    elif option == 'Date / Old':
        sorted_list = sorted(st.session_state.items_by_name.items(), key=lambda x: x[1].images[0].date_obj, reverse=False)

    if filter_text is not None and filter_text != '':
        sorted_list = filter(lambda x: filter_text in x[0], sorted_list)

    for name, item in sorted_list:
        
        if st.button(name, key=name):
            st.session_state.current_image = name

        lines = ["{0:.6f} date:{1:}".format(item.error, item.images[0].date_obj.strftime('%Y/%m/%d %H:%M:%S'))]
        html_lines = "".join([f'<p style="margin:0; line-height:1.1;">{line}</p>' for line in lines])
        st.markdown(html_lines, unsafe_allow_html=True)

        st.image(item.images[0].image)
        
        if item.error < error_threshold:
            st.badge("Success", icon=":material/check:", color="green")
        else:
            st.badge("Fail", color="red")


if st.session_state.current_image in st.session_state.items_by_name.keys():
    
    name = st.session_state.current_image

    item = st.session_state.items_by_name[name]
    
    st.write('--------')

    st.subheader('{}'.format(name))
    st.divider(width="stretch")
    st.write('lhs:{} / rhs:{}'.format(item.images[0].filepath, item.images[1].filepath))
    st.write('error:{0:.6f}'.format(item.error))
    
    image_comparison(
    img1=item.images[0].image,
    img2=item.images[1].image, width=image_width)

    st.image(item.error_map, width = image_width)
    
    
