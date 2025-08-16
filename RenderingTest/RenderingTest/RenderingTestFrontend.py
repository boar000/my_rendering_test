
from email.policy import default
import RenderingTestLib as rt
import os
from textwrap import indent
import numpy as np
import re
import time
import streamlit as st
import flip_evaluator as flip
from streamlit_image_comparison import image_comparison
from datetime import datetime, timedelta
from collections import defaultdict
import requests

directory = './images'
reference_directory = directory + '/reference'
extension = '.bmp'
error_threshold = 0.01

image_width = 800

# 状態を初期化
if "is_initialized" not in st.session_state:
    st.session_state.is_initialized = True
    st.session_state.current_test = None
    st.session_state.current_image = None
    st.session_state.test_cases = []
    st.session_state.items_by_name = {}
    st.session_state.latest_result = rt.TestSummary()
    
    st.session_state.items_by_name = rt.load_reference_images()
    st.session_state.test_cases = rt.gather_test_cases()

    
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

    test = st.selectbox("Version", tuple(p.name for p in st.session_state.test_cases))
    test = next((x for x in st.session_state.test_cases if x.name == test), None)
    if test != None:
        if st.session_state.current_test != test:
            st.session_state.current_test = test
            st.session_state.latest_result = rt.run_test(test, st.session_state.items_by_name)


    st.write("{}/{} passed test.".format(len(st.session_state.latest_result.passed), len(st.session_state.latest_result.passed) + len(st.session_state.latest_result.failed)))

    option = st.selectbox(
    "Sort by",
    ("Name", "Error"))
    
    filter_text = st.text_input(
    "Filter")
    
    show_passed = st.checkbox("passed", value=True)
    show_failed = st.checkbox("failed", value=True)
    show_not_found = st.checkbox("not found", value=False)

    if option == 'Name':
        sorted_list = sorted(st.session_state.items_by_name.items(), key=lambda x: x[0])
    elif option == 'Error':
        sorted_list = sorted(st.session_state.items_by_name.items(), key=lambda x: x[1].error)

    if filter_text is not None and filter_text != '':
        sorted_list = filter(lambda x: filter_text in x[0], sorted_list)

    #images = []
    #captions = []
    #
    #for name, item in sorted_list:
    #    images.append(item.reference.get_fullpath())
    #    captions.append(name)
    #    実用上問題ないかもしれないがimageを直接返すので例えば完全に同じバイト列が来た場合に正しくデータを特定できない    
    #    selected = image_select(label='', images=images, captions=captions)


    for name, item in sorted_list:
        
        show = False

        if show_passed: 
            if name in st.session_state.latest_result.passed:
                show = True

        if show_failed: 
            if name in st.session_state.latest_result.failed:
                show = True

        if show_not_found: 
            if name in st.session_state.latest_result.not_found:
                show = True
        
        if show == False:
            continue

        if st.button(name, key=name):
            st.session_state.current_image = name

        lines = ["error {0:.6f}".format(item.error)]
        html_lines = "".join([f'<p style="margin:0; line-height:1.1;">{line}</p>' for line in lines])
        st.markdown(html_lines, unsafe_allow_html=True)

        st.image(item.reference.image)
        
        #if item.error < error_threshold:
        #    st.badge("Success", icon=":material/check:", color="green")
        #else:
        #    st.badge("Fail", color="red")


st.write('--------')
api_test = st.text_input('api test')
if api_test:
    res = requests.get("http://localhost:8000/test-ci/{}".format(test.name))
    st.write(res.json())

if st.session_state.current_image in st.session_state.items_by_name.keys():
    
    name = st.session_state.current_image
    item = st.session_state.items_by_name[name]
    
    st.subheader('{}'.format(name))
    st.write('test:{}'.format(item.test.filepath).replace('\\', '/'))
    st.write('error:{0:.6f}'.format(item.error))
    
    image_comparison(
    img1=item.reference.image,
    img2=item.test.image, width=image_width)

    if item.error_map is not None:
        st.image(item.error_map, width = image_width)
    
    
