import os
import numpy as np
import re
import cv2
import time
import flip_evaluator as flip
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum

directory = './images'
reference_directory = directory + '/reference'
extension = '.bmp'
error_threshold = 0.01

class TestResult(Enum):
    Unknown = 0
    Passed = 1
    Failed = 2
    NotFound = 3

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
        self.result = TestResult.Unknown
        
    def reset(self):
        self.error = 0.0
        self.error_map = None
        self.test = None
        self.result = TestResult.Unknown
        
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
        self.total_count = 0
        
    def reset(self):
        self.passed = []
        self.failed = []
        self.not_found = []
        self.total_count = 0


def load_reference_images():
    result = {}

    for fname in os.listdir(reference_directory):
        if fname.endswith(extension):
            name = os.path.basename(fname).replace(extension, '')        
            result[name] = Item()

        image = ImageObject(date_obj = None, filepath = os.path.join(reference_directory, fname))
        image.load_image()
        
        result[name].reference = image
    
    return result

def gather_test_cases():
    pattern = re.compile(r"^(?P<name>.+)-(?P<date>\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})$")
    
    test_cases = []

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
                
                test_cases.append(TestCase(name=childdir, raw_folder_path=childdirfull, date=d))

    return test_cases

def get_file_names(test:TestCase):
    return os.listdir(test.raw_folder_path)

# Utility class for incremental test.
#
# Simplest usage. 
#  context = IncrementalTestContext()
#  context.initialize(test, items_by_name)
#
#  for file_name in context.file_names:
#      context.run_test_incremental(test, file_name, items_by_name)
#
#
class IncrementalTestContext:
    def __init__(self) -> None:
        self.file_names = []
        self.test_summary = TestSummary()
        
    def initialize(self, test:TestCase, items_by_name):
        self.file_names = get_file_names(test)
        
        not_found = list(items_by_name.keys())
        
        self.test_summary.total_count = len(not_found)
        self.test_summary.not_found = not_found

    def run_test_incremental(self, test:TestCase, file_name:str, items_by_name):
        name = os.path.basename(file_name).replace(extension, '')
        
        self.test_summary.not_found.remove(name)

        total = 0
        passed = 0

        if name in items_by_name:

            image = ImageObject(date_obj = None, filepath = os.path.join(test.raw_folder_path, file_name))
            image.load_image()

            items_by_name[name].test = image

            item = items_by_name[name]
            item.test = image

            flipErrorMap, meanFLIPError, parameters = flip.evaluate(
                item.reference.get_fullpath(),
                item.test.get_fullpath(), "LDR")
        
            item.error = meanFLIPError
            item.error_map = flipErrorMap

            if item.error < error_threshold:
                self.test_summary.passed.append(name)
                item.result = TestResult.Passed
            else:
                self.test_summary.failed.append(name)
                item.result = TestResult.Failed
              

# Run a test.
def run_test(test:TestCase, items_by_name):
    
    context = IncrementalTestContext()
    context.initialize(test, items_by_name)

    for file_name in context.file_names:
        context.run_test_incremental(test, file_name, items_by_name)
        
    return context.test_summary

