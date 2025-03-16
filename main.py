from openai import OpenAI
import re
import os
import json

# 配置文件路径
CONFIG_FILE = "api_config.json"

# 默认配置
DEFAULT_API = {
    "name": "默认 API",
    "base_url": "https://api.ppinfra.com/",
    "api_key": "sk_kuEi2Hgrp7SqCGSlxycmeBOY047_34FMoqj6J2FOw5o",
    "model": "deepseek/deepseek-v3/community",
    "max_tokens": 1024,
    "stream": True
}

# 初始化API配置
def load_config():
    """从文件加载配置，如果文件不存在则使用默认配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('apis', [DEFAULT_API]), config.get('current_api_index', 0)
        except:
            print("配置文件加载失败，使用默认配置")
    return [DEFAULT_API], 0

# 保存配置到文件
def save_config(apis, current_api_index):
    """保存配置到文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({'apis': apis, 'current_api_index': current_api_index}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"配置保存失败: {e}")

# 加载配置
apis, current_api_index = load_config()

def show_help():
    """显示帮助信息"""
    print("\n可用命令：")
    print("exit         - 退出程序")
    print("help         - 显示帮助信息")
    print("clear        - 清空当前对话历史")
    print("api_new      - 新建API配置")
    print("api_list     - 列出所有API配置")
    print("api_edit <编号> - 修改指定API配置")
    print("api_del <编号>  - 删除指定API配置")
    print("api_switch <编号> - 切换当前API配置")

def validate_url(url):
    """验证URL格式"""
    return re.match(r"^https?://\S+", url.strip())

def get_yes_no_input(prompt, default_yes=True):
    """获取用户是否确认的输入"""
    default = "Y/n" if default_yes else "y/N"
    response = input(f"{prompt} ({default}): ").lower().strip()
    
    if not response:
        return default_yes
    
    return response in ("y", "yes", "是", "确定")

def create_client(api_index):
    """创建指定API的客户端"""
    config = apis[api_index]
    return OpenAI(base_url=config["base_url"], api_key=config["api_key"])

def handle_api_new():
    """处理新建API配置"""
    global current_api_index, apis
    
    print("\n新建API配置：")
    name = input("输入您要新建的 API 别名: ").strip()
    base_url = input("输入您的 API 接入点: ").strip()
    api_key = input("输入您的 API Key: ").strip()
    model = input("输入该 API 使用的模型: ").strip()
    
    max_tokens_input = input("输入最大 Token: ").strip()
    max_tokens = 1024  # 默认值
    if max_tokens_input:
        try:
            max_tokens = int(max_tokens_input)
        except ValueError:
            print(f"Token数无效，使用默认值: {max_tokens}")
    
    stream = get_yes_no_input("使用流式传输吗", True)
    
    if not all([name, base_url, api_key]):
        print("API别名、接入点和Key不能为空！")
        return
        
    if not validate_url(base_url):
        print("无效的URL格式！")
        return
    
    if not model:
        model = DEFAULT_API["model"]
        print(f"使用默认模型: {model}")
    
    # 显示配置信息
    print("\n配置信息:")
    print(f"API别名: {name}")
    print(f"接入点: {base_url}")
    print(f"API Key: {api_key[:6]}*****")
    print(f"模型: {model}")
    print(f"最大Token: {max_tokens}")
    print(f"流式传输: {'是' if stream else '否'}")
    
    if get_yes_no_input("确定保存以上内容吗？", True):
        new_api = {
            "name": name,
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        apis.append(new_api)
        current_api_index = len(apis) - 1
        print("新建成功！")
        print(f"已切换到新API：{name}")
        save_config(apis, current_api_index)

def handle_api_edit(index):
    """处理编辑API配置"""
    global apis
    
    if index < 0 or index >= len(apis):
        print("无效的API编号！")
        return
    
    target = apis[index]
    print(f"\n您即将修改 '{target['name']}'")
    
    new_name = input(f"新别名（当前：{target['name']}）: ").strip() or target['name']
    new_url = input(f"新接入点（当前：{target['base_url']}）: ").strip() or target['base_url']
    new_key = input(f"新Key（当前：{target['api_key'][:6]}*****）: ").strip() or target['api_key']
    new_model = input(f"新模型（当前：{target.get('model', DEFAULT_API['model'])}）: ").strip() or target.get('model', DEFAULT_API['model'])
    
    current_max_tokens = target.get('max_tokens', DEFAULT_API['max_tokens'])
    max_tokens_input = input(f"新最大Token（当前：{current_max_tokens}）: ").strip()
    new_max_tokens = current_max_tokens
    if max_tokens_input:
        try:
            new_max_tokens = int(max_tokens_input)
        except ValueError:
            print(f"Token数无效，保持原值: {new_max_tokens}")
    
    current_stream = target.get('stream', DEFAULT_API['stream'])
    new_stream = get_yes_no_input(f"使用流式传输吗（当前：{'是' if current_stream else '否'}）", current_stream)
    
    if not validate_url(new_url):
        print("无效的URL格式！")
        return
    
    # 显示配置信息
    print("\n修改后配置信息:")
    print(f"API别名: {new_name}")
    print(f"接入点: {new_url}")
    print(f"API Key: {new_key[:6]}*****")
    print(f"模型: {new_model}")
    print(f"最大Token: {new_max_tokens}")
    print(f"流式传输: {'是' if new_stream else '否'}")
    
    if get_yes_no_input("确定保存以上内容吗？", True):
        apis[index] = {
            "name": new_name,
            "base_url": new_url,
            "api_key": new_key,
            "model": new_model,
            "max_tokens": new_max_tokens,
            "stream": new_stream
        }
        print("修改成功！")
        if index == current_api_index:
            print("注意：当前使用的API已更新配置")
        save_config(apis, current_api_index)

def handle_api_commands(command):
    """处理API管理命令"""
    global current_api_index, apis
    
    if command == "api_new":
        handle_api_new()
        return True
        
    elif command == "api_list":
        # 列出所有API配置
        print("\n当前所有API配置：")
        for i, api in enumerate(apis, 1):
            status = " (当前使用)" if i-1 == current_api_index else ""
            print(f"{i}. {api['name']}{status}")
            print(f"   接入点：{api['base_url']}")
            print(f"   模型：{api.get('model', DEFAULT_API['model'])}")
            print(f"   最大Token：{api.get('max_tokens', DEFAULT_API['max_tokens'])}")
            print(f"   流式传输：{'是' if api.get('stream', DEFAULT_API['stream']) else '否'}")
            print()
        return True
            
    elif command.startswith("api_edit "):
        # 修改API配置
        try:
            _, num = command.split(maxsplit=1)
            index = int(num)-1
            handle_api_edit(index)
            return True
        except Exception as e:
            print(f"无效的API编号或输入错误：{str(e)}")
            return True
            
    elif command.startswith("api_del "):
        # 删除API配置
        try:
            _, num = command.split(maxsplit=1)
            index = int(num)-1
            if index < 0 or index >= len(apis):
                print("无效的API编号！")
                return True
                
            if len(apis) == 1:
                print("不能删除最后一个API配置！")
                return True
                
            target = apis[index]
            if get_yes_no_input(f"确定要删除 '{target['name']}' 吗？", False):
                del apis[index]
                print("删除成功！")
                if current_api_index >= index:
                    current_api_index = max(0, current_api_index-1)
                save_config(apis, current_api_index)
            return True
                
        except Exception as e:
            print(f"无效的API编号或输入错误：{str(e)}")
            return True
            
    elif command.startswith("api_switch "):
        # 切换当前API
        try:
            _, num = command.split(maxsplit=1)
            index = int(num)-1
            if 0 <= index < len(apis):
                current_api_index = index
                print(f"已切换到：{apis[index]['name']}")
                save_config(apis, current_api_index)
            else:
                print("无效的API编号")
            return True
        except:
            print("使用方法：api_switch <编号>")
            return True
            
    return False

# 主程序
def main():
    """主程序入口"""
    messages = [{"role": "system", "content": "你是一个AI助手"}]
    
    print("欢迎使用AI聊天助手！输入内容开始对话（输入'exit'退出，输入'help'帮助）")
    print(f"当前API：{apis[current_api_index]['name']}")
    
    while True:
        try:
            user_input = input("\n你：").strip()
            if not user_input:
                continue
                
            if user_input.lower() == "exit":
                print("对话结束")
                break
                
            if user_input.lower() == "help":
                show_help()
                continue
                
            if user_input.lower() == "clear":
                messages = [{"role": "system", "content": "你是一个AI助手"}]
                print("对话历史已清空")
                continue
                
            # 处理API命令
            if handle_api_commands(user_input):
                continue
                
            # 正常对话流程
            messages.append({"role": "user", "content": user_input})
            
            # 获取当前API配置
            current_api = apis[current_api_index]
            model = current_api.get("model", DEFAULT_API["model"])
            max_tokens = current_api.get("max_tokens", DEFAULT_API["max_tokens"])
            stream = current_api.get("stream", DEFAULT_API["stream"])
            
            # 创建当前API的客户端
            client = create_client(current_api_index)
            
            print("AI：", end="", flush=True)
            
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=stream,
                    max_tokens=max_tokens,
                )
                
                full_response = []
                
                if stream:
                    for chunk in response:
                        content = chunk.choices[0].delta.content or ""
                        print(content, end="", flush=True)
                        full_response.append(content)
                else:
                    content = response.choices[0].message.content
                    print(content)
                    full_response.append(content)
                    
                print()  # 换行
                messages.append({"role": "assistant", "content": "".join(full_response)})
                
            except Exception as e:
                print(f"API请求失败: {str(e)}")
            
        except KeyboardInterrupt:
            print("\n对话已中断")
            save_config(apis, current_api_index)  # 保存配置
            break
            
        except Exception as e:
            print(f"\n发生错误：{str(e)}")
            
    # 退出前保存配置
    save_config(apis, current_api_index)

if __name__ == "__main__":
    main()
