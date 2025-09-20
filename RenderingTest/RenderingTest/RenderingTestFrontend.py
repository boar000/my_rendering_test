
from email.policy import default
from turtle import color
from types import NoneType
import RenderingTestLib as rt
import os
import numpy as np
import re
import time
import streamlit as st
import flip_evaluator as flip
from streamlit_image_comparison import image_comparison
from datetime import datetime, timedelta
from collections import defaultdict
import requests
from st_click_detector import click_detector
from PIL import Image
import cv2

@st.cache_data
def load_reference_images():
    return rt.load_reference_images()  

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
    st.session_state.refresh = False

    
def show_hdr_image(image : rt.ImageObject, exposure=0.0):
    try:
        if image.image is None:
            image.load_image()

        hdr = image.image.astype(np.float32) / 255.0  # [0,255] → [0,1]

        scale = 2.0 ** exposure
        img_scaled = np.clip(hdr * scale, 0, 1)  # HDR → [0,1] クリップ

        # ---- トーンマッピング (Reinhard など)
        ##tonemap = cv2.createTonemapReinhard(gamma=2.2)
        #ldr = tonemap.process(img_scaled.astype(np.float32))
        #img_scaled = np.clip(ldr * 255, 0, 255).astype(np.uint8)

        # ---- Streamlit で表示 (RGB順)
        st.image(img_scaled, width=image_width)
    except Exception as e:
        st.write("Error in show_hdr_image: {}".format(e))

def style():
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

    st.html(
        """
        <style>
        /* サイドバー全体の幅 */
        [data-testid="stSidebar"] {
            min-width: 400px;  /* デフォルトはおよそ 250px */
            max-width: 120000px;
        }
        </style>
        """
    ) 


    st.markdown(
        """
        <style>
        /* 全体のフォントサイズ */
        html, body, [class*="css"] {
            font-size: 13px !important;
        }

        /* コンテナ間の余白を縮める */
        .block-container {
            padding-top: 0.5rem;
            padding-bottom: 0.5rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        /* 各ウィジェット間の間隔 */
        .stMarkdown, .stButton, .stDataFrame, .stPlotlyChart, .stImage {
            margin-bottom: 0.3rem !important;
        }

        /* ヘッダーや見出しのフォント縮小 */
        h1, h2, h3, h4 {
            margin: 0.2em 0 !important;
            font-size: 90% !important;
        }

        /* テーブルやデータフレーム */
        .dataframe td, .dataframe th {
            padding: 2px 6px !important;
            font-size: 12px !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


style()

with st.sidebar:
    
    st.header("Rendering Test")

    status_text = st.empty()


    test = st.selectbox("Version", tuple(p.name for p in st.session_state.test_cases))

    force_run_test = st.button("(re)run test")

    c0, c1 = st.columns(2)
    with c0:
        st.text('Sort by')
    with c1:
        option = st.selectbox(
        "Sort by",
        ("Name", "Error"), label_visibility='collapsed')


    c0, c1 = st.columns(2)
    with c0:
        st.text('Filter')
    with c1:
        filter_text = st.text_input(
        "Filter", label_visibility='collapsed')

    display_type = st.radio(
        "Thunbnail",
        ["Test", "Reference"],
        index=0, label_visibility='collapsed')

    c0, c1, c2 = st.columns(3)
    with c0:
        show_passed = st.checkbox("passed", value=True)
    with c1:
        show_failed = st.checkbox("failed", value=True)
    with c2:
        show_not_found = st.checkbox("not found", value=False)
    st.divider()

    passed_text = st.empty()
    failed_text = st.empty()
    not_found_text = st.empty()

    test = next((x for x in st.session_state.test_cases if x.name == test), None)
    if test != None:
        if st.session_state.current_test != test or force_run_test or st.session_state.refresh == True:
            st.session_state.current_test = test
            st.session_state.refresh = False
            is_test_result_cached = os.path.exists(os.path.join(test.raw_folder_path, "report.json"))

            if is_test_result_cached and (force_run_test == False):
                st.session_state.latest_result.reset()
                st.session_state.latest_result.load(os.path.join(test.raw_folder_path, "report.json"))
                
                result = st.session_state.latest_result
                for name, item in st.session_state.items_by_name.items():
                    item.test = rt.ImageObject(date_obj = None, filepath = os.path.join(test.raw_folder_path, name + rt.extension))
                    item.test.create_thumbnail_if_not_exists()
                    item.result = rt.TestResult.NotFound
                    
                    if name in result.passed:
                        item.result = rt.TestResult.Passed
                    if name in result.failed:
                        item.result = rt.TestResult.Failed
                
            else:
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

                st.session_state.latest_result.save(os.path.join(test.raw_folder_path, "report.json"))
                    
                # clear placeholders for showing progress.
                status_text.empty()
                for itr in progress_text_place_holders:
                    itr.empty();
                for itr in progress_image_place_holders:
                    itr.empty();
                
                st.session_state.refresh = True
                st.rerun()


    if option == 'Name':
        sorted_list = sorted(st.session_state.items_by_name.items(), key=lambda x: x[0])
    elif option == 'Error':
        sorted_list = sorted(st.session_state.items_by_name.items(), key=lambda x: x[1].test.error)

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

    gallery_html = """
    <style>
    .gallery {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
    }
    .gallery-item {
        background: #000;
        border-radius: 2px;
        overflow: hidden;
    }
    .gallery-item img {
        width: 100%;
        height: auto;
        display: block;
    }
    .caption {
        text-align: center;
        color: white;
    }
    .caption.red { background-color: #e74c3c; }
    .caption.blue { background-color: #3498db; }
    .caption.green { background-color: #27ae60; }
    .caption.purple { background-color: #9b59b6; }
    .caption.glay { background-color: #404040; }
    </style>
    """
    
    gallery_html += '<div class="gallery">'

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

        b = '''
        if is_failed:
            if st.button(':red[{}]'.format(name), key=name):
                st.session_state.current_image = name
                
        elif is_passed:
            if st.button(':green[{}]'.format(name), key=name):
                st.session_state.current_image = name

        elif is_not_found:
            if st.button(':gray[{}]'.format(name), key=name, disabled=True):
                st.session_state.current_image = name
        '''

        disp_image = None
        if display_type == "Reference":
            disp_image = item.reference
        elif display_type == "Test":
            disp_image = item.test

        color = ""
        if is_passed:
            color = "green"
        if is_failed:
            color = "red"
        if is_not_found:
            color = "glay"

        gallery_html += f"""
            <a href='#' id='{name}'>
                <div class="gallery-item" onclick="selectItem('cat2')">
                    <div class="caption {color}">{name}</div>
                    <img src="{disp_image.get_thumbnail_url().replace("./static/","http://localhost:8501/app/static/" )}" />
                </div>
            </a>
        """


        tmp = '''
        lines = ["error {0:.6f}".format(item.test.error)]
        html_lines = "".join([f'<p style="margin:0; line-height:1.1;">{line}</p>' for line in lines])
        st.markdown(html_lines, unsafe_allow_html=True)

        if display_type == "Reference":
            st.image(item.reference.get_thumbnail_url())
        elif display_type == "Test":
            if item.result == rt.TestResult.NotFound:
                st.image(item.reference.get_thumbnail_url())
            else:
                st.image(item.test.get_thumbnail_url())

        '''
    gallery_html += "</div>"

    clicked = click_detector(gallery_html)
    st.session_state.current_image = clicked

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
    st.write('error:{0:.6f}'.format(item.test.error))
    
    image_comparison(
    img1=item.reference.get_thumbnail_url(),
    img2=item.test.get_thumbnail_url(), width=image_width)

    if item.test.error_map is not None:
        st.image(item.test.error_map, width = image_width)
    else:
        flipErrorMap, meanFLIPError, parameters = flip.evaluate(
            item.reference.get_fullpath(),
            item.test.get_fullpath(), "LDR")
        
        st.image(flipErrorMap)
    
    exposure = st.slider("Exposure (EV)", -4.0, 4.0, 0.0, 0.1, width=400)
    
    show_hdr_image(item.reference, exposure)
    show_hdr_image(item.test, exposure)