import requests
import base64
import json
import os
from PIL import Image
import io
import sys
import time

# 配置信息 - 替换为你的实际密钥
BAIDU_API_KEY = os.getenv("BAIDU_API_KEY")
BAIDU_SECRET_KEY = os.getenv("BAIDU_SECRET_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")  # 新增 DeepSeek API 密钥

def get_baidu_access_token():
    """获取百度API访问令牌"""
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_API_KEY}&client_secret={BAIDU_SECRET_KEY}"
    try:
        response = requests.post(url, timeout=60)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        print(f"获取百度Token失败: {str(e)}")
        return None

def process_image(image_path, max_size=1024):
    """处理图片：调整大小并转换为Base64编码"""
    try:
        img = Image.open(image_path)
        
        # 调整图片大小
        img.thumbnail((max_size, max_size))
        
        # 转换为字节流
        buffered = io.BytesIO()
        
        # 根据图片格式保存
        if img.format == 'PNG':
            img.save(buffered, format="PNG")
        else:
            img.save(buffered, format="JPEG")
        
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"图片处理失败: {str(e)}")
        return None

def recognize_landmark(image_path):
    """使用百度API识别地标"""
    # 1. 获取访问令牌
    access_token = get_baidu_access_token()
    if not access_token:
        return "获取百度API访问令牌失败"
    
    # 2. 处理图片
    img_base64 = process_image(image_path)
    if not img_base64:
        return "图片处理失败"
    
    # 3. 准备API请求
    baidu_url = f"https://aip.baidubce.com/rest/2.0/image-classify/v1/landmark?access_token={access_token}"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload = {'image': img_base64}
    
    # 4. 发送请求
    try:
        response = requests.post(baidu_url, headers=headers, data=payload, timeout=15)
        response.raise_for_status()
        result = response.json()
        
        # 5. 解析结果
        if 'result' in result:
            return result['result']
        elif 'error_msg' in result:
            return f"识别错误: {result['error_msg']}"
        return "地标识别失败，未返回有效结果"
    except Exception as e:
        return f"API请求失败: {str(e)}"

def get_landmark_explanation(landmark_info):
    """使用 DeepSeek API 获取地标讲解"""
    if not DEEPSEEK_API_KEY:
        return "错误: 未配置 DeepSeek API 密钥"
    
    # 构造提示词
    prompt = (
        f"你是一位专业的历史文化讲解员，请根据以下地标信息，提供详细的讲解：\n"
        f"地标名称: {landmark_info.get('name', '未知')}\n"
        f"位置: {landmark_info.get('location', '未知')}\n"
        f"显著性: {landmark_info.get('score', '未知')}\n\n"
        "请包括以下内容：\n"
        "1. 地标的历史背景和建造时期\n"
        "2. 建筑特点和文化意义\n"
        "3. 相关的重要历史事件\n"
        "4. 当前的功能和参观信息\n"
        "5. 有趣的小故事或冷知识\n\n"
        "用生动有趣的语言进行讲解，适合游客阅读。"
    )
    
    # 准备 API 请求
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一位专业的历史文化讲解员，擅长用生动有趣的方式讲解地标建筑的历史和文化背景。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        print("正在获取地标讲解...")
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        response.raise_for_status()
        result = response.json()
        
        # 解析响应
        if 'choices' in result and len(result['choices']) > 0:
            return result['choices'][0]['message']['content']
        else:
            return "未能获取讲解内容"
    except Exception as e:
        return f"获取讲解失败: {str(e)}"

def print_result(result):
    """打印识别结果和讲解"""
    print("\n地标识别结果:")
    
    if isinstance(result, dict):
        # 百度API的标准响应格式
        if 'landmark' in result:
            landmark_name = result['landmark']
            print(f"✅ 地标名称: {landmark_name}")
            print(f"🔍 置信度: {result.get('probability', 'N/A')}")
            print(f"📍 位置: {result.get('location', 'N/A')}")
            
            # 准备地标信息用于讲解
            landmark_info = {
                'name': landmark_name,
                'location': result.get('location', ''),
                'score': result.get('probability', '')
            }
            
            # 获取并打印讲解
            explanation = get_landmark_explanation(landmark_info)
            print("\n" + "="*50)
            print("地标讲解:")
            print(explanation)
            print("="*50)
        else:
            print("未识别到地标")
            
    elif isinstance(result, list) and result:
        # 处理多个结果的响应
        for i, item in enumerate(result, 1):
            print(f"\n结果 #{i}:")
            print(f"✅ 地标名称: {item.get('name', 'N/A')}")
            print(f"⭐ 显著性: {item.get('score', 'N/A')}")
            print(f"📍 位置: {item.get('location', 'N/A')}")
            
            # 获取并打印讲解
            explanation = get_landmark_explanation(item)
            print("\n" + "="*50)
            print("地标讲解:")
            print(explanation)
            print("="*50)
    else:
        print(result)

def main():
    """主程序"""
    print("=== 地标识别系统 ===")
    
    # 检查 DeepSeek API 密钥
    if not DEEPSEEK_API_KEY:
        print("警告: 未设置 DeepSeek API 密钥，将无法获取地标讲解")
        print("请设置环境变量: DEEPSEEK_API_KEY")
    
    # 获取图片路径
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = input("请输入图片路径: ").strip('"')
    
    # 检查文件是否存在
    if not os.path.isfile(image_path):
        print(f"错误: 文件不存在 - {image_path}")
        return
    
    # 检查文件大小
    file_size = os.path.getsize(image_path)
    if file_size > 4 * 1024 * 1024:  # 4MB
        print("错误: 图片文件过大 (最大支持4MB)")
        return
    
    print(f"处理图片: {os.path.basename(image_path)}")
    print("识别中，请稍候...")
    
    # 执行识别
    result = recognize_landmark(image_path)
    
    # 打印结果
    print_result(result)

if __name__ == "__main__":
    main()