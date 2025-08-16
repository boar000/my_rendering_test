
from email.policy import default
import os
from textwrap import indent
import numpy as np
import re
import cv2
import time
import streamlit as st
import flip_evaluator as flip
from streamlit_image_comparison import image_comparison
from datetime import datetime, timedelta
from collections import defaultdict
#from streamlit_image_select import image_select

directory = './images'
reference_directory = directory + '/reference'
extension = '.bmp'
error_threshold = 0.01

image_width = 800

class ImageObject:
    def __init__(self, date_obj: datetime = None, filepath: str = None) -> None:
        self.date_obj = date_obj
        self.filepath = filepath
        self.image = None
    
    def get_fullpath(self):
        return self.filepath

    def load_image(self):
        fullpath = self.get_fullpath()
        img = cv2.imread(fullpath)
        self.image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.image = np.asarray(self.image)

class Item:
    def __init__(self) -> None:
        self.error = 0.0
        self.error_map = None
        self.reference = None
        self.test = None
        self.passed = False
        
    def is_passed(self):
        return self.error < error_threshold
        
class TestCase:
    def __init__(self, name:str, raw_folder_path:str, date:datetime) -> None:
        self.name = name
        self.raw_folder_path = raw_folder_path
        self.date = date

class TestSummary:
    def __init__(self) -> None:
        self.passed = []
        self.failed = []
        self.not_found = []

def run_test(test:TestCase):
    
    result = TestSummary()

    not_found = list(st.session_state.items_by_name.keys())

    for fname in os.listdir(test.raw_folder_path):
        name = os.path.basename(fname).replace(extension, '')
        
        not_found.remove(name)

        total = 0
        passed = 0

        if name in st.session_state.items_by_name:

            image = ImageObject(date_obj = None, filepath = os.path.join(test.raw_folder_path, fname))
            image.load_image()

            st.session_state.items_by_name[name].test = image

            item = st.session_state.items_by_name[name]
            item.test = image

            flipErrorMap, meanFLIPError, parameters = flip.evaluate(
                item.reference.get_fullpath(),
                item.test.get_fullpath(), "LDR")
        
            item.error = meanFLIPError
            item.error_map = flipErrorMap

            if item.is_passed():
                result.passed.append(name)
            else:
                result.failed.append(name)
              
    result.not_found = not_found
    return result  

def load_reference_images():
    for fname in os.listdir(reference_directory):
        if fname.endswith(extension):
            name = os.path.basename(fname).replace(extension, '')        
            st.session_state.items_by_name[name] = Item()

        image = ImageObject(date_obj = None, filepath = os.path.join(reference_directory, fname))
        image.load_image()
        
        st.session_state.items_by_name[name].reference = image   

def gather_test_cases():
    pattern = re.compile(r"^(?P<name>.+)-(?P<date>\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})$")
    
    for childdir in os.listdir(directory):
        childdirfull = os.path.join(directory, childdir)
        if os.path.isdir(childdirfull):

            match = pattern.match(childdir)
            if match:
                testname = match.group("name")
                #if name not in st.session_state.items_by_name:
                #    st.session_state.items_by_name[name] = Item()

                date_str = match.group("date")
                d = datetime.strptime(date_str, "%Y-%m-%d-%H-%M-%S")
                
                st.session_state.test_cases.append(TestCase(name=testname, raw_folder_path=childdirfull, date=d))

# 状態を初期化
if "is_initialized" not in st.session_state:
    st.session_state.is_initialized = True
    st.session_state.current_test = None
    st.session_state.current_image = None
    st.session_state.test_cases = []
    st.session_state.items_by_name = {}
    st.session_state.latest_result = TestSummary()
    
    load_reference_images()
    gather_test_cases()

    
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
            st.session_state.latest_result = run_test(test)


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



if st.session_state.current_image in st.session_state.items_by_name.keys():
    
    name = st.session_state.current_image

    item = st.session_state.items_by_name[name]
    
    st.write('--------')

    st.subheader('{}'.format(name))
    st.divider(width="stretch")
    st.write('test:{}'.format(item.test.filepath).replace('\\', '/'))
    st.write('error:{0:.6f}'.format(item.error))
    
    image_comparison(
    img1=item.reference.image,
    img2=item.test.image, width=image_width)

    if item.error_map is not None:
        st.image(item.error_map, width = image_width)
    
    
