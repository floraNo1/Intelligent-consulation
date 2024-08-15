from flask import Flask, request, jsonify, render_template
import qianfan  # 对话生成的API库
import jieba  # 中文分词
import os
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.common.by import By
import pyautogui
import time
from datetime import datetime, timedelta

# 环境设置
os.environ["QIANFAN_ACCESS_KEY"] = "xxxxxx"
os.environ["QIANFAN_SECRET_KEY"] = "xxxxxx"

app = Flask(__name__)

# 定义医学科室相关词汇
keywords = [
    "心血管科", "内分泌科", "消化科", "神经科", "呼吸科", "肝病科", "肾内科", "感染科", "血液科",
    "风湿免疫科", "普通内科", "肛肠科", "男科", "神经内科", "皮肤顽症", "耳鼻喉科", "肿瘤科", "口腔科",
    "皮肤科", "神经脑外科", "眼科", "营养保健科", "肝胆科", "血管科", "新生儿科", "妇产科", "脊柱外科",
    "普通外科", "整形科", "关节科", "骨科", "心外科", "动脉导管未闭科", "健身科", "复杂先心病科", "精神心理科",
    "乳腺科", "传染病科", "颌面外科", "美容科", "结核病科", "内科", "产科", "老年科", "职业病科", "康复科",
    "疼痛科", "麻醉科", "急诊科", "重症医学科", "医学影像科", "核医学科", "超声科", "病理科", "中医科",
    "中西医结合科", "针灸科", "推拿科", "理疗科", "心理咨询科", "口腔正畸科", "口腔修复科", "口腔颌面外科",
    "口腔种植科", "口腔预防科", "放射科", "检验科", "输血科", "药剂科", "临床药学科", "营养科", "预防保健科"
]

for keyword in keywords:
    jieba.add_word(keyword)

def extract_departments(text):
    words = jieba.lcut(text)
    departments = {word for word in words if word in keywords}
    return list(departments)

@app.route('/')
def index():
    return render_template('chat1.html')

@app.route('/greet', methods=['GET'])
def greet():
    return jsonify({"reply": "您好，我是小翼！请问有什么能帮助您的吗？"})

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message')
    chat_comp = qianfan.ChatCompletion()
    messages = [{"role": "user", "content": user_input}]

    # 获取助手回复
    resp = chat_comp.do(model="ERNIE-Tiny-8K", messages=messages)
    assistant_reply = resp["body"]["result"]
    messages.append({"role": "assistant", "content": assistant_reply})

    # 提取科室名称
    final_departments = extract_departments(assistant_reply)
    disease_name = final_departments[0] if final_departments else ""

    return jsonify({"reply": assistant_reply, "departments": final_departments, "disease_name": disease_name})

@app.route('/autoregister', methods=['POST'])
def auto_register():
    data = request.json
    disease_name = data.get('disease_name')
    selected_date = data.get('timestamp')  # 获取前端日期

    print(f"Received data: {data}")  # 打印接收到的所有数据
    print(f"Selected date: {selected_date}")

    # 确保WebDriver路径正确
    edgedriver_path = os.path.abspath('./edgedriver_win64/msedgedriver.exe')
    if not os.path.exists(edgedriver_path):
        return jsonify({"error": "WebDriver not found at path: " + edgedriver_path})

    service = EdgeService(executable_path=edgedriver_path)
    driver = webdriver.Edge(service=service)
    driver.maximize_window()

    # 解析从前端获取的日期
    try:
        start_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid timestamp format."})

    end_date = start_date + timedelta(days=17)
    today = datetime.today().date()
    days_until_start = (start_date - today).days
    total_days = (end_date - start_date).days

    url = "https://expert.baidu.com/med/template/#/pages/guahao/hospitallist/index?title=%E6%8C%89%E5%8C%BB%E9%99%A2&sf_ref=&from=&fclk=king_%E6%8C%89%E5%8C%BB%E9%99%A2&lid=0287061935&referlid=3571811586&_=4cxci09iym4&ts=1722768576411"
    driver.get(url)
    time.sleep(10)  # 等待页面加载

    hospitals = driver.find_elements(By.CSS_SELECTOR, ".hospital-list.c-gap-inner-left-boundary.c-gap-inner-right-boundary > div")
    current_url = ""

    for index, hospital in enumerate(hospitals):
        try:
            hospital.click()
            time.sleep(2)

            # 搜索医生信息
            search = driver.find_element(By.CSS_SELECTOR, ".gh-search")
            search.click()
            time.sleep(2)

            search_box = driver.find_element(By.CSS_SELECTOR, ".gh-search > div > input")
            search_box.send_keys(disease_name)
            time.sleep(2)
            pyautogui.press('enter', presses=2)
            time.sleep(2)

            doctor_page_found = False
            for i in range(days_until_start, days_until_start + total_days + 1):
                try:
                    date_element = driver.find_element(By.CSS_SELECTOR, f"#date-{i}")
                    date_element.click()
                    time.sleep(2)

                    experts = driver.find_elements(By.CSS_SELECTOR, ".expert-list.static-padding.consult.experiment")
                    if experts:
                        experts[0].click()
                        time.sleep(2)
                        current_url = driver.current_url
                        # 使用 pyautogui 模拟点击预约按钮
                        screen_width, screen_height = pyautogui.size()
                        x = screen_width * 0.63
                        y = screen_height * 0.9
                        pyautogui.click(x, y)
                        time.sleep(10)
                        doctor_page_found = True
                        break
                except Exception as e:
                    print(f"Error finding date element: {e}")
                    continue

                time.sleep(2)

            if doctor_page_found:
                break

            driver.back()
            time.sleep(2)

        except Exception as e:
            print(f"Error handling hospital index {index}: {e}")

    driver.quit()

    if current_url:
        return jsonify({"current_url": current_url})
    else:
        return jsonify({"error": "No valid doctor details page URL found."})

if __name__ == '__main__':
    app.run(debug=True)
