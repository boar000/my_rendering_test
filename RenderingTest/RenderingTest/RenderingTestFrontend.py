
from email.policy import default
from turtle import color
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

@st.cache_data
def load_reference_images():
    return rt.load_reference_images()  

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
    
    st.session_state.items_by_name = load_reference_images()
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

    status_text = st.empty()

    test = st.selectbox("Version", tuple(p.name for p in st.session_state.test_cases))
        
    option = st.selectbox(
    "Sort by",
    ("Name", "Error"))
    
    filter_text = st.text_input(
    "Filter")
    
    display_type = st.radio(
    "Display type",
    ["Test", "Reference"],
    index=0,
)

    show_passed = st.checkbox("passed", value=True)
    show_failed = st.checkbox("failed", value=True)
    show_not_found = st.checkbox("not found", value=False)
    st.divider()

    passed_text = st.empty()
    failed_text = st.empty()
    not_found_text = st.empty()

    test = next((x for x in st.session_state.test_cases if x.name == test), None)
    if test != None:
        if st.session_state.current_test != test:
            st.session_state.current_test = test
            st.session_state.latest_result.reset()

            incremental_context = rt.IncrementalTestContext()
            incremental_context.initialize(test, st.session_state.items_by_name)
            
            items_by_name = st.session_state.items_by_name
            st.session_state.latest_result = incremental_context.test_summary

            # initialize placeholders for showing progress.
            progress_text_place_holders = []
            progress_image_place_holders = []

            for file_name in incremental_context.file_names:
                progress_text_place_holders.append(st.empty())          
                progress_image_place_holders.append(st.empty())           

            i = 0
            for file_name in incremental_context.file_names:
                status_text.text(f"processing... {file_name}")
                incremental_context.run_test_incremental(test, file_name, items_by_name)

                passed_text.write("{}/{} passed test.".format(len(st.session_state.latest_result.passed), st.session_state.latest_result.total_count))

                if len(st.session_state.latest_result.failed) > 0:
                    failed_text.text("failed : {}".format(len(st.session_state.latest_result.failed)))

                if len(st.session_state.latest_result.not_found) > 0:
                    not_found_text.text("data not found : {}".format(len(st.session_state.latest_result.not_found)))
                
                name = file_name.replace(rt.extension, '')

                if items_by_name[name].result == rt.TestResult.Passed:
                    progress_text_place_holders[i].write(':green[{}]'.format(name))
                elif items_by_name[name].result == rt.TestResult.Failed:
                    progress_text_place_holders[i].write(':red[{}]'.format(name))
                    
                progress_image_place_holders[i].image(items_by_name[name].test.image)

                i = i + 1
                    
            # clear placeholders for showing progress.
            status_text.empty()
            for itr in progress_text_place_holders:
                itr.empty();
            for itr in progress_image_place_holders:
                itr.empty();


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
        
        is_passed = item.result == rt.TestResult.Passed
        is_failed = item.result == rt.TestResult.Failed
        is_not_found = name in st.session_state.latest_result.not_found
        
        show = False
       
        if show_passed and is_passed:
            show = True
        
        if show_failed and is_failed:
            show = True

        if show_not_found and is_not_found:
            show = True
        
        if show == False:
            continue

        if is_failed:
            if st.button(':red[{}]'.format(name), key=name):
                st.session_state.current_image = name
                
        elif is_passed:
            if st.button(':green[{}]'.format(name), key=name):
                st.session_state.current_image = name

        elif is_not_found:
            if st.button(':gray[{}]'.format(name), key=name, disabled=True):
                st.session_state.current_image = name

        lines = ["error {0:.6f}".format(item.error)]
        html_lines = "".join([f'<p style="margin:0; line-height:1.1;">{line}</p>' for line in lines])
        st.markdown(html_lines, unsafe_allow_html=True)

        if display_type == "Reference":
            st.image(item.reference.image)
        elif display_type == "Test":
            st.image(item.test.image)


st.write('--------')
api_test = st.text_input('api test : input test version here.')
if api_test:
    res = requests.get("http://localhost:8000/test-ci/{}".format(api_test))
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
    
    
