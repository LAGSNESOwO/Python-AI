import sys
import os
import json
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTextEdit, QLineEdit, QPushButton, QTabWidget, QLabel, QComboBox,
                             QSpinBox, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QDialog, QFormLayout, QInputDialog, QSplitter, 
                             QFrame, QToolBar, QAction, QStatusBar, QMenu, QSystemTrayIcon)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QTextCursor, QFont, QColor, QPalette
from openai import OpenAI

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

# 颜色主题
DARK_THEME = {
    "bg_color": "#2b2b2b",
    "text_color": "#e0e0e0",
    "input_bg": "#3c3f41", 
    "user_msg": "#6ca5ff",
    "bot_msg": "#8be9fd",
    "accent": "#61afef",
    "button_bg": "#4b5263",
    "button_hover": "#5294e2",
    "border": "#4a4a4a"
}

LIGHT_THEME = {
    "bg_color": "#f5f5f5",
    "text_color": "#333333",
    "input_bg": "#ffffff",
    "user_msg": "#1a73e8",
    "bot_msg": "#0f9d58",
    "accent": "#1a73e8",
    "button_bg": "#e0e0e0",
    "button_hover": "#bbdefb",
    "border": "#d0d0d0"
}

# 当前主题 (默认暗色)
CURRENT_THEME = DARK_THEME


# 用于处理API请求的线程
class ApiRequestThread(QThread):
    response_received = pyqtSignal(str)
    chunk_received = pyqtSignal(str)
    request_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, api_config, messages):
        super().__init__()
        self.api_config = api_config
        self.messages = messages
        
    def run(self):
        try:
            client = OpenAI(
                base_url=self.api_config["base_url"], 
                api_key=self.api_config["api_key"]
            )
            
            stream = self.api_config.get("stream", True)
            max_tokens = self.api_config.get("max_tokens", 1024)
            model = self.api_config.get("model", DEFAULT_API["model"])
            
            response = client.chat.completions.create(
                model=model,
                messages=self.messages,
                stream=stream,
                max_tokens=max_tokens,
            )
            
            full_response = []
            
            if stream:
                for chunk in response:
                    content = chunk.choices[0].delta.content or ""
                    self.chunk_received.emit(content)
                    full_response.append(content)
            else:
                content = response.choices[0].message.content
                self.response_received.emit(content)
                full_response = [content]
                
            self.response_received.emit("".join(full_response))
            self.request_finished.emit()
            
        except Exception as e:
            self.error_occurred.emit(str(e))
            self.request_finished.emit()


# 主应用窗口
class ChatApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能聊天助手")
        self.setMinimumSize(900, 600)
        
        # 加载配置
        self.load_config()
        
        # 初始化UI
        self.init_ui()
        
        # 初始化聊天历史
        self.messages = [{"role": "system", "content": "你是一个AI助手"}]
        
        # 应用主题
        self.apply_theme()
    
    def load_config(self):
        """从文件加载配置"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.apis = config.get('apis', [DEFAULT_API])
                    self.current_api_index = config.get('current_api_index', 0)
            except:
                self.apis = [DEFAULT_API]
                self.current_api_index = 0
        else:
            self.apis = [DEFAULT_API]
            self.current_api_index = 0
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'apis': self.apis, 
                    'current_api_index': self.current_api_index
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "保存配置失败", f"无法保存配置: {str(e)}")
    
    def init_ui(self):
        """初始化用户界面"""
        # 创建主分割器
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.main_splitter)
        
        # 创建左侧聊天面板
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        self.chat_layout.setSpacing(10)
        
        # 聊天历史显示区域
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFontPointSize(11)
        self.chat_layout.addWidget(self.chat_display)
        
        # 输入区域
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        self.chat_input = QTextEdit()
        self.chat_input.setPlaceholderText("输入消息...")
        self.chat_input.setFixedHeight(70)
        self.chat_input.setAcceptRichText(False)
        
        send_button = QPushButton("发送")
        send_button.setFixedWidth(80)
        send_button.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(send_button)
        
        self.chat_layout.addWidget(input_container)
        
        # 创建右侧配置面板
        self.config_widget = QTabWidget()
        self.config_widget.setFixedWidth(300)
        
        # API配置标签页
        self.api_tab = QWidget()
        api_layout = QVBoxLayout(self.api_tab)
        
        # API选择下拉框
        api_selector_layout = QHBoxLayout()
        api_selector_layout.addWidget(QLabel("当前API:"))
        
        self.api_selector = QComboBox()
        self.api_selector.currentIndexChanged.connect(self.switch_api)
        api_selector_layout.addWidget(self.api_selector)
        
        api_layout.addLayout(api_selector_layout)
        
        # API列表
        self.api_table = QTableWidget(0, 2)
        self.api_table.setHorizontalHeaderLabels(["名称", "操作"])
        self.api_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.api_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.api_table.setColumnWidth(1, 100)
        api_layout.addWidget(self.api_table)
        
        # API管理按钮
        api_buttons_layout = QHBoxLayout()
        add_api_button = QPushButton("添加")
        add_api_button.clicked.connect(self.add_api)
        api_buttons_layout.addWidget(add_api_button)
        
        api_layout.addLayout(api_buttons_layout)
        
        # 当前API详情
        self.api_details = QTextEdit()
        self.api_details.setReadOnly(True)
        self.api_details.setMaximumHeight(150)
        api_layout.addWidget(QLabel("当前API详情:"))
        api_layout.addWidget(self.api_details)
        
        # 设置标签页
        self.settings_tab = QWidget()
        settings_layout = QVBoxLayout(self.settings_tab)
        
        # 主题选择
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("界面主题:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["暗色主题", "亮色主题"])
        self.theme_combo.currentIndexChanged.connect(self.change_theme)
        theme_layout.addWidget(self.theme_combo)
        settings_layout.addLayout(theme_layout)
        
        # 字体大小
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("字体大小:"))
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 24)
        self.font_size.setValue(11)
        self.font_size.valueChanged.connect(self.change_font_size)
        font_layout.addWidget(self.font_size)
        settings_layout.addLayout(font_layout)
        
        # 添加标签页
        self.config_widget.addTab(self.api_tab, "API配置")
        self.config_widget.addTab(self.settings_tab, "设置")
        
        # 添加到主分割器
        self.main_splitter.addWidget(self.chat_widget)
        self.main_splitter.addWidget(self.config_widget)
        self.main_splitter.setSizes([600, 300])
        
        # 创建工具栏
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(18, 18))
        
        # 工具栏按钮
        clear_action = QAction("清空聊天", self)
        clear_action.triggered.connect(self.clear_chat)
        toolbar.addAction(clear_action)
        
        save_action = QAction("保存聊天记录", self)
        save_action.triggered.connect(self.save_chat)
        toolbar.addAction(save_action)
        
        self.addToolBar(toolbar)
        
        # 状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("准备就绪")
        
        # 更新API列表显示
        self.update_api_lists()
        
        # 设置Enter键发送消息
        self.chat_input.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """事件过滤器，用于处理快捷键"""
        if obj == self.chat_input and event.type() == event.KeyPress:
            if event.key() == Qt.Key_Return and event.modifiers() != Qt.ShiftModifier:
                self.send_message()
                return True
        return super().eventFilter(obj, event)
    
    def update_api_lists(self):
        """更新API列表显示"""
        # 更新下拉框
        self.api_selector.clear()
        for api in self.apis:
            self.api_selector.addItem(api["name"])
        self.api_selector.setCurrentIndex(self.current_api_index)
        
        # 更新表格
        self.api_table.setRowCount(0)
        for i, api in enumerate(self.apis):
            row = self.api_table.rowCount()
            self.api_table.insertRow(row)
            
            # 名称
            name_item = QTableWidgetItem(api["name"])
            name_item.setData(Qt.UserRole, i)  # 存储API索引
            self.api_table.setItem(row, 0, name_item)
            
            # 操作按钮容器
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            
            # 编辑按钮
            edit_btn = QPushButton("编辑")
            edit_btn.setProperty("api_index", i)
            edit_btn.clicked.connect(lambda _, btn=edit_btn: self.edit_api(btn.property("api_index")))
            
            # 删除按钮
            delete_btn = QPushButton("删除")
            delete_btn.setProperty("api_index", i)
            delete_btn.clicked.connect(lambda _, btn=delete_btn: self.delete_api(btn.property("api_index")))
            
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(delete_btn)
            self.api_table.setCellWidget(row, 1, btn_widget)
        
        # 更新当前API详情
        self.update_api_details()
    
    def update_api_details(self):
        """更新当前API详情显示"""
        if self.current_api_index >= 0 and self.current_api_index < len(self.apis):
            api = self.apis[self.current_api_index]
            details = (
                f"名称: {api['name']}\n"
                f"接入点: {api['base_url']}\n"
                f"API Key: {api['api_key'][:6]}*****\n"
                f"模型: {api.get('model', DEFAULT_API['model'])}\n"
                f"最大Token: {api.get('max_tokens', DEFAULT_API['max_tokens'])}\n"
                f"流式传输: {'是' if api.get('stream', DEFAULT_API['stream']) else '否'}"
            )
            self.api_details.setText(details)
    
    def add_api(self):
        """添加新API"""
        dialog = ApiDialog(self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            new_api = dialog.get_api_data()
            self.apis.append(new_api)
            self.current_api_index = len(self.apis) - 1
            self.update_api_lists()
            self.save_config()
            QMessageBox.information(self, "添加成功", f"API '{new_api['name']}' 已添加并设为当前API")
    
    def edit_api(self, index):
        """编辑API"""
        if index < 0 or index >= len(self.apis):
            return
            
        dialog = ApiDialog(self, self.apis[index])
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            self.apis[index] = dialog.get_api_data()
            self.update_api_lists()
            self.save_config()
            QMessageBox.information(self, "编辑成功", f"API '{self.apis[index]['name']}' 已更新")
    
    def delete_api(self, index):
        """删除API"""
        if index < 0 or index >= len(self.apis):
            return
            
        if len(self.apis) <= 1:
            QMessageBox.warning(self, "无法删除", "至少需要保留一个API配置")
            return
            
        confirm = QMessageBox.question(
            self, 
            "确认删除", 
            f"确定要删除API '{self.apis[index]['name']}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            api_name = self.apis[index]["name"]
            del self.apis[index]
            
            if self.current_api_index >= index:
                self.current_api_index = max(0, self.current_api_index - 1)
                
            self.update_api_lists()
            self.save_config()
            QMessageBox.information(self, "删除成功", f"API '{api_name}' 已删除")
    
    def switch_api(self, index):
        """切换当前使用的API"""
        if 0 <= index < len(self.apis) and index != self.current_api_index:
            self.current_api_index = index
            self.update_api_details()
            self.save_config()
            self.statusBar.showMessage(f"已切换到API: {self.apis[index]['name']}")
    
    def send_message(self):
        """发送消息"""
        user_input = self.chat_input.toPlainText().strip()
        if not user_input:
            return
            
        # 清空输入框
        self.chat_input.clear()
        
        # 显示用户消息
        self.display_user_message(user_input)
        
        # 添加到消息历史
        self.messages.append({"role": "user", "content": user_input})
        
        # 显示AI正在思考
        self.statusBar.showMessage("AI正在思考...")
        
        # 创建并启动API请求线程
        self.request_thread = ApiRequestThread(
            self.apis[self.current_api_index],
            self.messages
        )
        self.request_thread.chunk_received.connect(self.handle_chunk)
        self.request_thread.response_received.connect(self.handle_response)
        self.request_thread.error_occurred.connect(self.handle_error)
        self.request_thread.request_finished.connect(self.finish_request)
        
        self.chat_display.append('<div style="color: #888888; margin: 5px 0;">AI思考中...</div>')
        self.ai_response_html = f'<div style="background-color: {CURRENT_THEME["bot_msg"]}15; padding: 10px; border-radius: 10px; margin: 5px 0; color: {CURRENT_THEME["bot_msg"]}; word-wrap: break-word;">【AI】: '
        self.request_thread.start()
    
    def handle_chunk(self, chunk):
        """处理流式响应的数据块"""
        # 更新最后一个div (移除最后的</div>并添加新内容)
        html = self.chat_display.toHtml()
        html = html.rsplit('</div>', 1)[0]
        html += self.escape_html(chunk) + '</div></body></html>'
        
        self.chat_display.setHtml(html)
        self.chat_display.moveCursor(QTextCursor.End)
        
        # 更新累积的响应
        self.ai_response_html += self.escape_html(chunk)
    
    def handle_response(self, response):
        """处理完整响应"""
        self.messages.append({"role": "assistant", "content": response})
        
        # 更新UI (如果不是流式传输)
        current_api = self.apis[self.current_api_index]
        if not current_api.get("stream", True):
            self.display_ai_message(response)
    
    def handle_error(self, error_msg):
        """处理API请求错误"""
        error_html = f'<div style="color: #ff5252; margin: 5px 0;">错误: {error_msg}</div>'
        self.chat_display.append(error_html)
        self.chat_display.moveCursor(QTextCursor.End)
    
    def finish_request(self):
        """请求完成后的处理"""
        # 移除"AI思考中"的提示并添加完整的消息
        html = self.chat_display.toHtml()
        html = html.replace('<div style="color: #888888; margin: 5px 0;">AI思考中...</div>', '')
        self.chat_display.setHtml(html)
        
        # 添加完整的AI响应
        self.chat_display.append(self.ai_response_html + '</div>')
        self.chat_display.moveCursor(QTextCursor.End)
        
        self.statusBar.showMessage("准备就绪")
    
    def display_user_message(self, message):
        """显示用户消息"""
        html = f'<div style="background-color: {CURRENT_THEME["user_msg"]}15; padding: 10px; border-radius: 10px; margin: 5px 0; color: {CURRENT_THEME["user_msg"]}; text-align: right; word-wrap: break-word;">【你】: {self.escape_html(message)}</div>'
        self.chat_display.append(html)
        self.chat_display.moveCursor(QTextCursor.End)
    
    def display_ai_message(self, message):
        """显示AI消息"""
        html = f'<div style="background-color: {CURRENT_THEME["bot_msg"]}15; padding: 10px; border-radius: 10px; margin: 5px 0; color: {CURRENT_THEME["bot_msg"]}; word-wrap: break-word;">【AI】: {self.escape_html(message)}</div>'
        self.chat_display.append(html)
        self.chat_display.moveCursor(QTextCursor.End)
    
    def escape_html(self, text):
        """转义HTML特殊字符"""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
    
    def clear_chat(self):
        """清空聊天记录"""
        confirm = QMessageBox.question(
            self, 
            "确认清空", 
            "确定要清空所有聊天记录吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            self.chat_display.clear()
            self.messages = [{"role": "system", "content": "你是一个AI助手"}]
            self.statusBar.showMessage("聊天记录已清空")
    
    def save_chat(self):
        """保存聊天记录"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_history_{timestamp}.html"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.chat_display.toHtml())
            
            QMessageBox.information(
                self, 
                "保存成功", 
                f"聊天记录已保存至: {filename}"
            )
        except Exception as e:
            QMessageBox.warning(
                self, 
                "保存失败", 
                f"无法保存聊天记录: {str(e)}"
            )
    
    def change_theme(self, index):
        """切换界面主题"""
        global CURRENT_THEME
        CURRENT_THEME = DARK_THEME if index == 0 else LIGHT_THEME
        self.apply_theme()
    
    def apply_theme(self):
        """应用当前主题"""
        # 创建应用程序样式表
        style = f"""
        QMainWindow, QDialog {{
            background-color: {CURRENT_THEME["bg_color"]};
            color: {CURRENT_THEME["text_color"]};
        }}
        
        QTextEdit, QLineEdit, QComboBox, QSpinBox {{
            background-color: {CURRENT_THEME["input_bg"]};
            color: {CURRENT_THEME["text_color"]};
            border: 1px solid {CURRENT_THEME["border"]};
            border-radius: 5px;
            padding: 5px;
        }}
        
        QPushButton {{
            background-color: {CURRENT_THEME["button_bg"]};
            color: {CURRENT_THEME["text_color"]};
            border: none;
            border-radius: 5px;
            padding: 5px 10px;
            min-height: 25px;
        }}
        
        QPushButton:hover {{
            background-color: {CURRENT_THEME["button_hover"]};
        }}
        
        QTableWidget {{
            background-color: {CURRENT_THEME["input_bg"]};
            color: {CURRENT_THEME["text_color"]};
            border: 1px solid {CURRENT_THEME["border"]};
            gridline-color: {CURRENT_THEME["border"]};
            border-radius: 5px;
        }}
        
        QHeaderView::section {{
            background-color: {CURRENT_THEME["button_bg"]};
            color: {CURRENT_THEME["text_color"]};
            padding: 5px;
            border: 1px solid {CURRENT_THEME["border"]};
        }}
        
        QTabWidget::pane {{
            border: 1px solid {CURRENT_THEME["border"]};
            border-radius: 5px;
            background-color: {CURRENT_THEME["bg_color"]};
        }}
        
        QTabBar::tab {{
            background-color: {CURRENT_THEME["button_bg"]};
            color: {CURRENT_THEME["text_color"]};
            border: 1px solid {CURRENT_THEME["border"]};
            border-bottom: none;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
            padding: 8px 12px;
            margin-right: 2px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {CURRENT_THEME["accent"]};
            color: white;
        }}
        
        QStatusBar {{
            background-color: {CURRENT_THEME["bg_color"]};
            color: {CURRENT_THEME["text_color"]};
            border-top: 1px solid {CURRENT_THEME["border"]};
        }}
        
        QToolBar {{
            background-color: {CURRENT_THEME["bg_color"]};
            border-bottom: 1px solid {CURRENT_THEME["border"]};
            spacing: 5px;
        }}
        
        QToolButton {{
            background-color: transparent;
            color: {CURRENT_THEME["text_color"]};
            border: none;
            border-radius: 5px;
            padding: 5px;
        }}
        
        QToolButton:hover {{
            background-color: {CURRENT_THEME["button_hover"]};
        }}
        """
        
        # 应用样式表
        self.setStyleSheet(style)
        
        # 刷新聊天显示
        chat_html = self.chat_display.toHtml()
        self.chat_display.clear()
        self.chat_display.setHtml(chat_html)
    
    def change_font_size(self, size):
        """更改字体大小"""
        font = self.chat_display.font()
        font.setPointSize(size)
        self.chat_display.setFont(font)
        
        self.chat_input.setFont(font)
    
    def closeEvent(self, event):
        """程序关闭时保存配置"""
        self.save_config()
        event.accept()


# API配置对话框
class ApiDialog(QDialog):
    def __init__(self, parent=None, api_data=None):
        super().__init__(parent)
        
        self.api_data = api_data or {}
        self.setWindowTitle("API配置" if api_data else "新建API")
        self.setMinimumWidth(400)
        
        self.init_ui()
        self.apply_theme()
    
    def init_ui(self):
        """初始化对话框UI"""
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # API名称
        self.name_input = QLineEdit()
        self.name_input.setText(self.api_data.get("name", ""))
        form_layout.addRow("API名称:", self.name_input)
        
        # 接入点
        self.url_input = QLineEdit()
        self.url_input.setText(self.api_data.get("base_url", ""))
        form_layout.addRow("接入点:", self.url_input)
        
        # API Key
        self.key_input = QLineEdit()
        self.key_input.setText(self.api_data.get("api_key", ""))
        self.key_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("API Key:", self.key_input)
        
        # 模型
        self.model_input = QLineEdit()
        self.model_input.setText(self.api_data.get("model", DEFAULT_API["model"]))
        form_layout.addRow("模型:", self.model_input)
        
        # 最大Token
        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(1, 16000)
        self.max_tokens.setValue(self.api_data.get("max_tokens", DEFAULT_API["max_tokens"]))
        form_layout.addRow("最大Token:", self.max_tokens)
        
        # 流式传输
        self.stream_check = QCheckBox()
        self.stream_check.setChecked(self.api_data.get("stream", DEFAULT_API["stream"]))
        form_layout.addRow("流式传输:", self.stream_check)
        
        layout.addLayout(form_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def get_api_data(self):
        """获取表单数据"""
        return {
            "name": self.name_input.text(),
            "base_url": self.url_input.text(),
            "api_key": self.key_input.text(),
            "model": self.model_input.text(),
            "max_tokens": self.max_tokens.value(),
            "stream": self.stream_check.isChecked()
        }
    
    def accept(self):
        """验证并接受对话框"""
        name = self.name_input.text().strip()
        url = self.url_input.text().strip()
        key = self.key_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "验证失败", "API名称不能为空")
            return
            
        if not url:
            QMessageBox.warning(self, "验证失败", "接入点不能为空")
            return
            
        if not key:
            QMessageBox.warning(self, "验证失败", "API Key不能为空")
            return
            
        # 验证URL格式
        if not re.match(r"^https?://\S+", url):
            QMessageBox.warning(self, "验证失败", "接入点URL格式无效")
            return
            
        super().accept()
    
    def apply_theme(self):
        """应用主题"""
        self.setStyleSheet(self.parent().styleSheet())


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 使用Fusion样式以获得更一致的跨平台外观
    
    window = ChatApp()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
