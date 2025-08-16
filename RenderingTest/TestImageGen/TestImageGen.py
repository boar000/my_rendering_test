import cv2
import os
import random
import re
from datetime import datetime, timedelta
from collections import defaultdict

# 日付範囲を設定
start_date = datetime(2000, 1, 1)
end_date = datetime(2025, 12, 31)

# 日付の範囲を日数で計算
days_range = (end_date - start_date).days

srcpath = 'images/test001.bmp'
srcpath2 = 'images/test001-r.bmp'


img = cv2.imread(srcpath)
img2 = cv2.imread(srcpath2)
#img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


for t in range(30):

    filepath = srcpath.replace('test001', 'test{:03}'.format(t))

    #for i in range(5):
    #    # ランダム日付生成
    #    random_days = i#random.randint(0, days_range)
    #    random_date = start_date + timedelta(days=random_days)
    #
    #    print(filepath)
    #
    #    dst_dir = "./images/" + random_date.strftime('%Y-%m-%d-%H-%M-%S')
    #
    #    try:
    #        
    #        os.makedirs(dst_dir)
    #    except:
    #        ''' do nothing '''
    #
    #    dstpath = dst_dir + '/' + os.path.basename(filepath).replace('-l', '')
    #    cv2.imwrite(dstpath, img2)

    dstpath = './images/reference/' + os.path.basename(filepath).replace('-l', '')
    
    cv2.imwrite(dstpath, img)

    #print('--------------------')

files_by_name = defaultdict(list)
pattern = re.compile(r"^(?P<name>.+)-(?P<date>\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})\.bmp$")
for fname in os.listdir('./images'):
    match = pattern.match(fname)
    if match:
        name = match.group("name")
        date_str = match.group("date")
        date_obj = datetime.strptime(date_str, "%Y-%m-%d-%H-%M-%S")
        files_by_name[name].append((date_obj, fname))


# 各NAMEごとに日付順でソート＆連番付け
for name, file_list in files_by_name.items():
    file_list.sort(key=lambda x: x[0])  # 日付でソート

        
#cv2.imwrite()