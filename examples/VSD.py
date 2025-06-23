#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生命体征实时监测系统 - Vital Signs Detection (VSD)
功能：使用毫米波雷达实时监测呼吸率和心率
作者：ASTRI团队
版本：1.0
"""

# 导入系统和数学库
import sys
import numpy as np
import queue
from datetime import datetime
from math import ceil
# 导入PyQt5界面库
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, QProgressBar,
                             QComboBox, QDesktopWidget, QGridLayout, QSizePolicy, QGraphicsDropShadowEffect)
# 导入Qt核心模块，用于定时器和常量
from PyQt5.QtCore import QTimer, Qt
# 导入Qt字体和图形模块
from PyQt5.QtGui import QFont, QLinearGradient, QColor, QPalette, QBrush, QPixmap
# 导入pyqtgraph用于实时数据可视化
import pyqtgraph as pg
# 导入串口工具模块
import serial.tools.list_ports
# 导入操作系统和时间模块
import os
import time

# 将项目根目录添加到系统路径
sys.path.append('.')

# 导入自定义模块
from adc_reader import AdcReader  # ADC数据读取模块
from examples.range_bin_analyzer import RangeBinAnalyzer  # 距离区间分析模块
from examples.vital_signs_analyzer import VitalSignsAnalyzer  # 生命体征分析模块

class VitalSignsGUI(QMainWindow):
    """
    生命体征监测GUI主界面类
    功能：提供图形化界面显示实时呼吸率和心率数据
    """
    
    def __init__(self):
        """
        初始化GUI界面和相关参数
        设置窗口布局、图表配置、数据存储等
        """
        super().__init__()
        
        # 设置窗口基本属性
        self.setWindowTitle("生命体征监测系统 - Vital Signs Monitor")  # 窗口标题
        self.setWindowState(Qt.WindowMaximized)  # 窗口最大化显示
        
        # 获取屏幕尺寸信息
        desktop = QDesktopWidget()
        screen_rect = desktop.screenGeometry()
        self.screen_width = screen_rect.width()   # 屏幕宽度
        self.screen_height = screen_rect.height() # 屏幕高度
        
        # 设置默认字体
        self.default_font = QFont("Microsoft YaHei", 10)  # 微软雅黑字体
        self.setFont(self.default_font)
        
        # 初始化数据存储变量
        self.data_queue = queue.Queue()      # 数据队列，用于线程间通信
        self.recorded_frames = []            # 记录的雷达帧数据
        self.time_points = []               # 时间点数据（分钟）
        self.br_values = []                 # 呼吸率数值列表
        self.hr_values = []                 # 心率数值列表
        self.point_count = 0                # 数据点计数器
        
        # 雷达配置参数
        self.num_adc_samples = 128          # ADC采样点数
        self.BR = None                      # 原始呼吸率数据
        self.HR = None                      # 原始心率数据
        
        # 调用界面初始化方法
        self.init_ui()

    def init_ui(self):
        """
        初始化用户界面
        创建主要的界面布局和组件
        """
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 设置全局样式表，消除所有可能的边框问题
        self.setStyleSheet("""
            QWidget {
                outline: none;
                border: none;
            }
            QWidget:focus {
                outline: none;
                border: none;
            }
            QLabel {
                outline: none;
                border: none;
            }
            QVBoxLayout, QHBoxLayout {
                outline: none;
                border: none;
            }
        """)
        
        # 创建主布局（垂直布局）
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)  # 去除边距
        main_layout.setSpacing(10)  # 设置组件间距
        
        # === 创建顶部标题栏 ===
        top_widget = QWidget()
        top_widget.setFixedHeight(80)  # 固定高度80像素
        # 设置蓝色渐变背景
        top_widget.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 #1976d2, stop:1 #2196f3);
            border-radius: 8px;
        """)
        
        # 顶部标题栏水平布局
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(25, 15, 25, 15)  # 设置内边距
        top_layout.setSpacing(20)  # 设置间距
        
        # 创建主标题
        title_label = QLabel("生命体征实时监测系统")
        title_label.setStyleSheet("""
            color: white;
            font-size: 28px;
            font-weight: bold;
            background: transparent;
        """)
        
        # === 创建控制面板 ===
        control_widget = QWidget()
        control_widget.setStyleSheet("background: transparent;")
        control_layout = QHBoxLayout(control_widget)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(15)  # 控件间距
        
        # 串口选择标签
        port_label = QLabel("串口:")
        port_label.setStyleSheet("""
            color: white;
            font-size: 14px;
            font-weight: bold;
            background: transparent;
        """)
        
        # 串口选择下拉框
        self.port_combo = QComboBox()
        self.port_combo.setFixedSize(120, 35)  # 固定尺寸
        self.port_combo.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 2px solid #1565c0;
                border-radius: 8px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: bold;
                color: #1565c0;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #1565c0;
            }
        """)
        
        # 刷新串口按钮
        self.refresh_button = QPushButton("🔄刷新")
        self.refresh_button.setFixedSize(80, 35)
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.9);
                border: 2px solid white;
                border-radius: 8px;
                color: #1976d2;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: white;
                border-color: #42a5f5;
            }
            QPushButton:pressed {
                background-color: #e3f2fd;
            }
        """)
        self.refresh_button.clicked.connect(self.refresh_ports)  # 连接刷新方法
        
        # === 清空日志按钮 ===
        self.clear_logs_button = QPushButton("🧹清空日志")
        self.clear_logs_button.setFixedSize(90, 35)
        self.clear_logs_button.setStyleSheet("""
            QPushButton {
                background-color: #ffeb3b;
                border: 2px solid #fbc02d;
                border-radius: 8px;
                color: #bf360c;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #fffde7;
                border-color: #fbc02d;
            }
            QPushButton:pressed {
                background-color: #ffe082;
            }
        """)
        self.clear_logs_button.clicked.connect(self.clear_logs)
        
        # 开始/停止监测按钮
        self.start_button = QPushButton("▶ 开始监测")
        self.start_button.setFixedSize(120, 35)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                border: 2px solid #4caf50;
                border-radius: 8px;
                color: white;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #66bb6a;
                border-color: #66bb6a;
            }
            QPushButton:pressed {
                background-color: #389e0d;
            }
        """)
        self.start_button.clicked.connect(self.start_acquisition)  # 连接开始采集方法
        
        # 将控件添加到控制面板布局
        control_layout.addWidget(port_label)
        control_layout.addWidget(self.port_combo)
        control_layout.addWidget(self.refresh_button)
        control_layout.addWidget(self.clear_logs_button)
        control_layout.addWidget(self.start_button)
        
        # === ASTRI Logo ===
        logo_container = QWidget()
        logo_container.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.1);
            border: none;
            border-radius: 6px;
        """)
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(10, 4, 10, 4)
        
        # 加载并缩放logo图片
        logo_label = QLabel()
        pixmap = QPixmap("images/astri_logo.png")
        logo_label.setPixmap(pixmap.scaledToHeight(26, Qt.SmoothTransformation))
        logo_layout.addWidget(logo_label)
        
        # 将组件添加到顶部布局
        top_layout.addWidget(title_label)       # 主标题
        top_layout.addStretch()                 # 弹性空间
        top_layout.addWidget(logo_container)    # ASTRI logo
        top_layout.addSpacing(20)              # logo和控制面板间距
        top_layout.addWidget(control_widget)   # 控制面板
        
        main_layout.addWidget(top_widget)
        
        # 初始化可用串口列表
        self.refresh_ports()
        
        # === 创建主要内容区域 ===
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            background-color: white;
            border: 1px solid #e8e8e8;
            border-radius: 8px;
        """)
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(20)
        
        # === 配置图表区域 ===
        pg.setConfigOptions(antialias=True)  # 启用抗锯齿
        plot_widget = pg.GraphicsLayoutWidget()
        plot_widget.setBackground('w')      # 白色背景
        plot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # 设置plot_widget内部行/列间距为4像素
        plot_widget.ci.setSpacing(4)
        
        # 创建右侧数值显示区域
        values_widget = QWidget()
        # 设置较小的最小宽度，不设置最大宽度
        min_width = 220
        values_widget.setMinimumWidth(min_width)
        # 不设置最大宽度，让其自适应
        values_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        values_widget.setStyleSheet("background-color: transparent;")
        
        values_layout = QVBoxLayout(values_widget)
        # 使用紧凑边距
        values_layout.setContentsMargins(8, 4, 8, 4)
        values_layout.setSpacing(8)
        
        # === 呼吸率卡片 ===
        br_card = QWidget()
        br_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        # 使用相对高度，但设置合理的最小/最大值
        min_card_height = max(140, int(self.screen_height * 0.16))
        max_card_height = min(220, int(self.screen_height * 0.22))
        br_card.setMinimumHeight(min_card_height)
        br_card.setMaximumHeight(max_card_height)
        br_card.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #e3f2fd, stop:0.3 #bbdefb, 
                    stop:0.7 #90caf9, stop:1 #64b5f6);
                border: none;
                border-radius: 20px;
                outline: none;
            }
            QWidget:focus {
                border: none;
                outline: none;
            }
        """)
        br_card.setFocusPolicy(Qt.NoFocus)
        br_main_layout = QVBoxLayout(br_card)
        card_margin = max(8, int(self.screen_height * 0.01))
        br_main_layout.setContentsMargins(card_margin, card_margin, card_margin, card_margin)
        br_main_layout.setSpacing(max(4, int(self.screen_height * 0.006)))
        # 顶部装饰条
        br_decorator = QWidget()
        br_decorator.setFixedHeight(max(3, int(self.screen_height * 0.005)))
        br_decorator.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                stop:0 #1976d2, stop:1 #42a5f5); 
            border-radius: 2px;
            border: none;
        """)
        br_main_layout.addWidget(br_decorator)
        # --- 距离显示标签，移除这里的添加 ---
        self.br_distance_label = QLabel("目标距离: -- m")
        self.br_distance_label.setStyleSheet("""
            color: #1976d2;
            font-size: 14px;
            font-weight: bold;
            background: transparent;
            border: none;
            outline: none;
        """)
        self.br_distance_label.setAlignment(Qt.AlignCenter)
        # br_main_layout.addWidget(self.br_distance_label)  # 注释掉原来的位置
        # 图标+标题组
        br_title_row = QWidget()
        br_title_row.setStyleSheet("background: transparent; border: none; outline: none;")
        br_title_row.setFocusPolicy(Qt.NoFocus)
        br_title_row_layout = QHBoxLayout(br_title_row)
        title_margin = max(5, int(self.screen_width * 0.005))
        br_title_row_layout.setContentsMargins(title_margin, 0, title_margin, 0)
        br_title_row_layout.setSpacing(max(8, int(self.screen_width * 0.008)))
        icon_size = max(30, min(50, int(min(self.screen_width, self.screen_height) * 0.04)))
        br_icon_container = QWidget()
        br_icon_container.setFixedSize(icon_size, icon_size)
        br_icon_container.setStyleSheet(f"""
            background: rgba(255,255,255,0.95); 
            border-radius: {icon_size//2}px; 
            border: none;
            outline: none;
        """)
        br_icon_container.setFocusPolicy(Qt.NoFocus)
        br_icon_layout = QVBoxLayout(br_icon_container)
        br_icon_layout.setContentsMargins(0,0,0,0)
        br_icon_layout.setAlignment(Qt.AlignCenter)
        br_icon_label = QLabel("🫁")
        icon_font_size = max(16, int(icon_size * 0.6))
        br_icon_label.setStyleSheet(f"""
            background: transparent; 
            border: none; 
            font-size: {icon_font_size}px;
            outline: none;
        """)
        br_icon_label.setAlignment(Qt.AlignCenter)
        br_icon_label.setFocusPolicy(Qt.NoFocus)
        br_icon_layout.addWidget(br_icon_label)
        br_text_group = QWidget()
        br_text_group.setStyleSheet("background: transparent; border: none; outline: none;")
        br_text_group.setFocusPolicy(Qt.NoFocus)
        br_text_layout = QVBoxLayout(br_text_group)
        br_text_layout.setContentsMargins(0, 0, 0, 0)
        br_text_layout.setSpacing(2)
        title_font = max(16, min(24, int(self.screen_height * 0.022)))
        subtitle_font = max(10, min(16, int(self.screen_height * 0.013)))
        br_chinese = QLabel("呼吸率")
        br_chinese.setStyleSheet(f"""
            color: #0d47a1; 
            font-size: {title_font}px; 
            font-weight: bold; 
            background: transparent; 
            border: none;
            outline: none;
        """)
        br_chinese.setFocusPolicy(Qt.NoFocus)
        br_english = QLabel("Breathing Rate")
        br_english.setStyleSheet(f"""
            color: #1976d2; 
            font-size: {subtitle_font}px; 
            font-weight: 500; 
            background: transparent; 
            border: none;
            outline: none;
        """)
        br_english.setFocusPolicy(Qt.NoFocus)
        br_text_layout.addWidget(br_chinese)
        br_text_layout.addWidget(br_english)
        br_title_row_layout.addWidget(br_icon_container)
        br_title_row_layout.addWidget(br_text_group)
        br_title_row_layout.addStretch()
        # --- 将距离标签添加到标题行的右侧 ---
        # br_title_row_layout.addWidget(self.br_distance_label)  # 注释掉卡片内的位置
        br_main_layout.addWidget(br_title_row)
        # --- 数值显示区域（垂直居中，数字和单位同一行） ---
        br_value_area = QWidget()
        br_value_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        br_value_area.setStyleSheet("""
            QWidget {
                background: rgba(255,255,255,0.95); 
                border-radius: 15px; 
                border: none;
                outline: none;
            }
            QWidget:focus {
                border: none;
                outline: none;
            }
        """)
        br_value_area.setFocusPolicy(Qt.NoFocus)
        br_value_vlayout = QVBoxLayout(br_value_area)
        br_value_vlayout.setContentsMargins(0, 0, 0, 0)
        br_value_vlayout.setSpacing(0)
        br_value_vlayout.addStretch(1)
        br_value_hlayout = QHBoxLayout()
        br_value_hlayout.setContentsMargins(0, 0, 0, 0)
        br_value_hlayout.setSpacing(8)
        br_value_hlayout.addStretch(1)
        value_font = max(32, min(72, int(self.screen_height * 0.06)))
        self.br_value_label = QLabel("0.0")
        self.br_value_label.setStyleSheet(f"""
            color: #0d47a1;
            font-size: {value_font}px;
            font-weight: 900;
            background: transparent;
            border: none;
            outline: none;
        """)
        self.br_value_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        br_unit = QLabel("BPM")
        br_unit.setStyleSheet(f"""
            color: #1565c0;
            font-size: {int(value_font*0.45)}px;
            font-weight: bold;
            background: transparent;
            border: none;
            outline: none;
        """)
        br_unit.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        br_value_hlayout.addWidget(self.br_value_label)
        br_value_hlayout.addWidget(br_unit)
        br_value_hlayout.addStretch(1)
        br_value_vlayout.addLayout(br_value_hlayout)
        br_value_vlayout.addStretch(1)
        br_main_layout.addWidget(br_value_area)
        # === 心率卡片 ===
        hr_card = QWidget()
        hr_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        hr_card.setMinimumHeight(min_card_height)
        hr_card.setMaximumHeight(max_card_height)
        hr_card.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #fff3e0, stop:0.3 #ffe0b2, 
                    stop:0.7 #ffcc80, stop:1 #ffb74d);
                border: none;
                border-radius: 20px;
                outline: none;
            }
            QWidget:focus {
                border: none;
                outline: none;
            }
        """)
        hr_card.setFocusPolicy(Qt.NoFocus)
        hr_main_layout = QVBoxLayout(hr_card)
        hr_main_layout.setContentsMargins(card_margin, card_margin, card_margin, card_margin)
        hr_main_layout.setSpacing(max(4, int(self.screen_height * 0.006)))
        hr_decorator = QWidget()
        hr_decorator.setFixedHeight(max(3, int(self.screen_height * 0.005)))
        hr_decorator.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                stop:0 #f57c00, stop:1 #ff9800); 
            border-radius: 2px;
            border: none;
        """)
        hr_main_layout.addWidget(hr_decorator)
        hr_title_row = QWidget()
        hr_title_row.setStyleSheet("background: transparent; border: none; outline: none;")
        hr_title_row.setFocusPolicy(Qt.NoFocus)
        hr_title_row_layout = QHBoxLayout(hr_title_row)
        hr_title_row_layout.setContentsMargins(title_margin, 0, title_margin, 0)
        hr_title_row_layout.setSpacing(max(8, int(self.screen_width * 0.008)))
        hr_icon_container = QWidget()
        hr_icon_container.setFixedSize(icon_size, icon_size)
        hr_icon_container.setStyleSheet(f"""
            background: rgba(255,255,255,0.95); 
            border-radius: {icon_size//2}px; 
            border: none;
            outline: none;
        """)
        hr_icon_container.setFocusPolicy(Qt.NoFocus)
        hr_icon_layout = QVBoxLayout(hr_icon_container)
        hr_icon_layout.setContentsMargins(0,0,0,0)
        hr_icon_layout.setAlignment(Qt.AlignCenter)
        hr_icon_label = QLabel("❤️")
        hr_icon_label.setStyleSheet(f"""
            background: transparent; 
            border: none; 
            font-size: {icon_font_size}px;
            outline: none;
        """)
        hr_icon_label.setAlignment(Qt.AlignCenter)
        hr_icon_label.setFocusPolicy(Qt.NoFocus)
        hr_icon_layout.addWidget(hr_icon_label)
        hr_text_group = QWidget()
        hr_text_group.setStyleSheet("background: transparent; border: none; outline: none;")
        hr_text_group.setFocusPolicy(Qt.NoFocus)
        hr_text_layout = QVBoxLayout(hr_text_group)
        hr_text_layout.setContentsMargins(0, 0, 0, 0)
        hr_text_layout.setSpacing(2)
        hr_chinese = QLabel("心率")
        hr_chinese.setStyleSheet(f"""
            color: #bf360c; 
            font-size: {title_font}px; 
            font-weight: bold; 
            background: transparent; 
            border: none;
            outline: none;
        """)
        hr_chinese.setFocusPolicy(Qt.NoFocus)
        hr_english = QLabel("Heart Rate")
        hr_english.setStyleSheet(f"""
            color: #f57c00; 
            font-size: {subtitle_font}px; 
            font-weight: 500; 
            background: transparent; 
            border: none;
            outline: none;
        """)
        hr_english.setFocusPolicy(Qt.NoFocus)
        hr_text_layout.addWidget(hr_chinese)
        hr_text_layout.addWidget(hr_english)
        hr_title_row_layout.addWidget(hr_icon_container)
        hr_title_row_layout.addWidget(hr_text_group)
        hr_title_row_layout.addStretch()
        hr_main_layout.addWidget(hr_title_row)
        # --- 数值显示区域（垂直居中，数字和单位同一行） ---
        hr_value_area = QWidget()
        hr_value_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        hr_value_area.setStyleSheet("""
            QWidget {
                background: rgba(255,255,255,0.95); 
                border-radius: 15px; 
                border: none;
                outline: none;
            }
            QWidget:focus {
                border: none;
                outline: none;
            }
        """)
        hr_value_area.setFocusPolicy(Qt.NoFocus)
        hr_value_vlayout = QVBoxLayout(hr_value_area)
        hr_value_vlayout.setContentsMargins(0, 0, 0, 0)
        hr_value_vlayout.setSpacing(0)
        hr_value_vlayout.addStretch(1)
        hr_value_hlayout = QHBoxLayout()
        hr_value_hlayout.setContentsMargins(0, 0, 0, 0)
        hr_value_hlayout.setSpacing(8)
        hr_value_hlayout.addStretch(1)
        self.hr_value_label = QLabel("0.0")
        self.hr_value_label.setStyleSheet(f"""
            color: #bf360c;
            font-size: {value_font}px;
            font-weight: 900;
            background: transparent;
            border: none;
            outline: none;
        """)
        self.hr_value_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        hr_unit = QLabel("BPM")
        hr_unit.setStyleSheet(f"""
            color: #e65100;
            font-size: {int(value_font*0.45)}px;
            font-weight: bold;
            background: transparent;
            border: none;
            outline: none;
        """)
        hr_unit.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        hr_value_hlayout.addWidget(self.hr_value_label)
        hr_value_hlayout.addWidget(hr_unit)
        hr_value_hlayout.addStretch(1)
        hr_value_vlayout.addLayout(hr_value_hlayout)
        hr_value_vlayout.addStretch(1)
        hr_main_layout.addWidget(hr_value_area)
        # --- 卡片间距和边距 ---
        values_layout.addSpacing(20)  # 距离标签和卡片之间的小间距
        values_layout.addWidget(self.br_distance_label)
        values_layout.addSpacing(4)  # 距离标签和卡片之间的小间距
        values_layout.addWidget(br_card)
        values_layout.addSpacing(140)  # 两个卡片之间的间距
        values_layout.addWidget(hr_card)
        values_layout.addStretch(1)  # 只在底部添加一个弹性空间
        
        content_layout.addWidget(plot_widget, 6)
        content_layout.addWidget(values_widget, 2)
        
        main_layout.addWidget(content_widget)
        
        # 底部进度条
        progress_widget = QWidget()
        progress_widget.setStyleSheet("""
            background-color: white;
            border: 1px solid #e8e8e8;
            border-radius: 8px;
        """)
        progress_widget.setFixedHeight(60)
        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.setContentsMargins(20, 15, 20, 15)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(1024)
        self.progress_bar.setFormat("数据采集进度: %v/1024 (%p%)")
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #d9d9d9;
                border-radius: 10px;
                text-align: center;
                font-size: 12px;
                font-weight: bold;
                color: #595959;
                background-color: #f5f5f5;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                          stop:0 #1890ff, stop:1 #40a9ff);
                border-radius: 9px;
            }
        """)
        
        progress_layout.addWidget(self.progress_bar)
        main_layout.addWidget(progress_widget)
        
        # 配置图表
        # 配置呼吸率图表
        self.br_plot = plot_widget.addPlot(row=0, col=0)
        self.br_plot.setContentsMargins(150, 0, 0, 0)
        self.br_plot.setTitle("🫁呼吸率监测 Breathing Rate Monitor", size="16pt", color='#1565c0')
        labelStyle = {'color': '#424242', 'font-size': '13pt', 'font-family': 'Microsoft YaHei'}
        self.br_plot.setLabel('left', text='呼吸率 (BPM)', **labelStyle)
        self.br_plot.setLabel('bottom', text='时间 Time (min)', **labelStyle)
        self.br_plot.showGrid(x=True, y=True, alpha=0.2)
        self.br_plot.getAxis('left').setStyle(tickFont=self.default_font)
        self.br_plot.getAxis('bottom').setStyle(tickFont=self.default_font)
        # 配置呼吸率图表刻度
        self.br_plot.showAxis('left')
        self.br_plot.showAxis('bottom')
        self.br_plot.setYRange(10, 40, padding=0)
        self.br_plot.getAxis('left').setTicks([[(i, str(i)) for i in range(10, 41, 5)]])
        
        # 设置X轴刻度（时间，分钟）
        self.num_points=0;
        self.TimeEnd = (self.num_points-1)/6;
        if self.TimeEnd <= 6:
            self.TimeEnd = 6;
    
        major_ticks = [(i, str(i)) for i in range(self.TimeEnd-6,self.TimeEnd+2)]
        minor_ticks = [(i/6, '') for i in range((self.TimeEnd-6)*6,(self.TimeEnd+1)*6) if i % 6 != 0]
        self.br_plot.getAxis('bottom').setTicks([major_ticks, minor_ticks])
        self.br_plot.setXRange(self.TimeEnd-6,self.TimeEnd, padding=0.01)

        
        # 配置呼吸率曲线样式
        self.br_curve = self.br_plot.plot(pen=pg.mkPen('#1976d2', width=4),
                                        symbol='o',
                                        symbolSize=6,
                                        symbolBrush='#42a5f5',
                                        symbolPen=pg.mkPen('#1565c0', width=2))
        
        # 配置心率图表
        plot_widget.nextRow()
        self.hr_plot = plot_widget.addPlot(row=1, col=0)
        self.hr_plot.setContentsMargins(150, 0, 0, 0)
        self.hr_plot.setTitle("❤️心率监测 Heart Rate Monitor", size="16pt", color='#e65100')
        self.hr_plot.setLabel('left', text='心率 (BPM)', **labelStyle)
        self.hr_plot.setLabel('bottom', text='时间 Time (min)', **labelStyle)
        self.hr_plot.showGrid(x=True, y=True, alpha=0.2)
        self.hr_plot.getAxis('left').setStyle(tickFont=self.default_font)
        self.hr_plot.getAxis('bottom').setStyle(tickFont=self.default_font)
        # 配置心率图表刻度 - 扩大显示范围
        self.hr_plot.showAxis('left')
        self.hr_plot.showAxis('bottom')
        self.hr_plot.setYRange(40, 140, padding=0)  # 从40-120扩大到40-140
        self.hr_plot.getAxis('left').setTicks([[(i, str(i)) for i in range(40, 141, 20)]])  # 刻度间隔改为20
        self.hr_plot.getAxis('bottom').setTicks([major_ticks, minor_ticks])
        self.hr_plot.setXRange(self.TimeEnd-6,self.TimeEnd, padding=0.01)
        
        
        # 配置心率曲线样式
        self.hr_curve = self.hr_plot.plot(pen=pg.mkPen('#f57c00', width=4),
                                        symbol='o',
                                        symbolSize=6,
                                        symbolBrush='#ff9800',
                                        symbolPen=pg.mkPen('#e65100', width=2))
        
        # 初始化定时器
        self.update_timer = QTimer()  # 创建定时器
        self.update_timer.timeout.connect(self.update_data)  # 连接定时器超时事件
        self.start_time = None  # 初始化开始时间
        
        self.adc_reader = None  # 初始化ADC读取器实例为空
        
        # 创建日志文件
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        now = datetime.now()
        self.log_file = os.path.join(log_dir, f"vitals_{now.strftime('%Y%m%d_%H%M%S')}.txt")

    def refresh_ports(self):
        """刷新并更新可用串口列表"""
        self.port_combo.clear()  # 清空串口下拉框
        # 获取所有可用串口
        ports = [port.device for port in serial.tools.list_ports.comports()]
        
        # 确保COM16在列表中（默认端口）
        default_port = "COM16"
        if default_port not in ports:
            ports.append(default_port)  # 如果COM16不在列表中，添加它
        
        # 排序并添加端口列表
        ports.sort()  # 对端口列表进行排序
        self.port_combo.addItems(ports)  # 将端口添加到下拉框
        
        # 设置COM16为默认选项
        default_index = self.port_combo.findText(default_port)  # 查找COM16的索引
        if default_index >= 0:
            self.port_combo.setCurrentIndex(default_index)  # 设置为当前选项
        
    def start_acquisition(self):
        """开始数据采集过程"""
        if self.adc_reader is None:  # 如果ADC读取器未初始化
            if self.port_combo.currentText():  # 如果选择了串口
                port = self.port_combo.currentText()  # 获取选中的串口
                # 重置数据存储
                self.point_count = 0  # 重置点计数器
                self.br_values = []  # 清空呼吸率值列表
                self.hr_values = []  # 清空心率值列表
                
                # 初始化ADC读取器
                self.adc_reader = AdcReader(  # 创建ADC读取器实例
                    radar_serial_port=port,  # 设置雷达串口
                    radar_cfg_path="radar_config/iwrl6432_2.cfg",  # 设置雷达配置文件路径
                    out_queue=self.data_queue  # 设置数据输出队列
                )
                self.adc_reader.start_acquisition()  # 启动数据采集
                self.update_timer.start(100)  # 启动定时器，每100ms更新一次
                self.start_button.setText("⏹ 停止监测")  # 更改按钮文本
                self.port_combo.setEnabled(False)  # 禁用串口选择
                self.refresh_button.setEnabled(False)  # 禁用刷新按钮
                self.progress_bar.setValue(0)  # 重置进度条
        else:
            self.stop_acquisition()  # 如果已经在采集，则停止
            
    def stop_acquisition(self):
        """停止数据采集过程"""
        if self.adc_reader:  # 如果ADC读取器存在
            self.adc_reader.stop_acquisition()  # 停止数据采集
            self.adc_reader.close()  # 关闭ADC读取器
            self.adc_reader = None  # 清除ADC读取器实例
            self.update_timer.stop()  # 停止定时器
            self.start_button.setText("▶ 开始监测")  # 更改按钮文本
            self.port_combo.setEnabled(True)  # 启用串口选择
            self.refresh_button.setEnabled(True)  # 启用刷新按钮
            self.progress_bar.setValue(0)  # 重置进度条
            self.recorded_frames = []
            self.br_values = []
            self.hr_values = []
            self.num_points = 0
            self.TimeEnd = 0
            
    def update_data(self):
        """更新数据显示的方法"""
        # 从队列中获取数据
        while not self.data_queue.empty():  # 当队列不为空时
            frame = self.data_queue.get()  # 获取一帧数据
            self.recorded_frames.append(frame)  # 将数据添加到记录列表
            
        # 更新进度条
        self.progress_bar.setValue(len(self.recorded_frames))  # 更新进度条值
        
        # 当收集到足够的帧数时处理数据
        if len(self.recorded_frames) >= 1024:  # 如果收集到1024帧数据
        # if len(self.recorded_frames) >= 100:
            self.adc_reader.save_to_npz(
                file_path=f"logs/frame_dump_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mat",
                config_metadata=self.adc_reader.get_radar_config(),
                recorded_frames=self.recorded_frames
            )
            self.process_frames()  # 处理数据帧
            
    def process_frames(self):
        """处理雷达数据帧的方法"""
        try:
            # 将数据帧转换为numpy数组
            recorded_frames_array = np.array(self.recorded_frames)  # 转换为numpy数组
            selected_chirp = recorded_frames_array[:, 0, :, :]  # 选择第一个chirp信号
            
            # 获取实际的ADC采样点数
            actual_adc_samples = selected_chirp.shape[-1]  # 获取最后一个维度的大小

            
            # 应用汉宁窗（使用实际的采样点数）
            window = np.hanning(actual_adc_samples)  # 创建汉宁窗
            chirp_windowed = selected_chirp * window  # 应用窗函数
            
            # FFT处理
            range_fft_complex = np.fft.fft(chirp_windowed, n=actual_adc_samples, axis=2)  # 进行FFT变换
            range_fft_magnitude = np.abs(range_fft_complex[:, :, :actual_adc_samples // 2])  # 计算幅度谱
            
            # 寻找目标距离区间
            analyzer = RangeBinAnalyzer()  # 创建距离区间分析器
            max_range_bin = analyzer.range_bin(range_fft_magnitude, display_or_not=False)  # 获取最大回波区间
            # --- 计算距离并更新标签 ---
            if(max_range_bin == 0):
                self.br_distance_label.setText("<font color='red'>没有检测到胸腔</font>")
                self.recorded_frames = [];
                self.progress_bar.setValue(0)  # 重置进度条
                self.recorded_frames = []
                self.br_values = []
                self.hr_values = []
                self.num_points = 0
                self.TimeEnd = 0
            else:
                range_resolution = 0.0234  # 每个bin的距离分辨率，单位米 (c/(2*BANDWIDTH))
                distance = max_range_bin * range_resolution
                self.br_distance_label.setText(f"<font color='#1976d2'>目标距离: {distance:.2f} m</font>")
            
                # 提取相位数据
                target_range_bin_complex = range_fft_complex[:,:, max_range_bin]  # 提取目标区间的复数数据
                phase_raw = np.angle(target_range_bin_complex)  # 计算相位角
                phase_unwrapped = np.unwrap(phase_raw, axis=0)  # 进行相位解缠绕
                
                # 分析生命体征
                vital_analyzer = VitalSignsAnalyzer()  # 创建生命体征分析器
                periodicity = 0.05  # 设置采样周期（秒）
                self.BR, self.HR = vital_analyzer.display3s(phase_unwrapped, periodicity, display_or_not=False)  # 分析呼吸率和心率
                
                # 处理呼吸率数据
                BR_filtered = self.BR.copy()  # 复制呼吸率数据
                mb = np.abs(np.mean(BR_filtered) - BR_filtered)  # 计算与均值的偏差
                while len(BR_filtered) > 1:  # 当还有多个数据点时
                    max_idx = np.argmax(mb)  # 找到最大偏差的索引
                    max_val = mb[max_idx]  # 获取最大偏差值
                    if max_val < 1:  # 如果最大偏差小于1
                        break  # 退出循环
                    BR_filtered = np.delete(BR_filtered, max_idx)  # 删除异常值
                    mb = np.abs(np.mean(BR_filtered) - BR_filtered)  # 重新计算偏差
                avg_br = np.mean(BR_filtered)  # 计算平均呼吸率
                
                # 处理心率数据
                HR_filtered = self.HR.copy()  # 复制心率数据
                mb = np.abs(np.mean(HR_filtered) - HR_filtered)  # 计算与均值的偏差
                while len(HR_filtered) > 1:  # 当还有多个数据点时
                    max_idx = np.argmax(mb)  # 找到最大偏差的索引
                    max_val = mb[max_idx]  # 获取最大偏差值
                    if max_val < 5:  # 如果最大偏差小于5（心率阈值）
                        break  # 退出循环
                    HR_filtered = np.delete(HR_filtered, max_idx)  # 删除异常值
                    mb = np.abs(np.mean(HR_filtered) - HR_filtered)  # 重新计算偏差
                avg_hr = np.mean(HR_filtered)  # 计算平均心率
                
                # 数据范围检查和过滤
                if 9 <= avg_br <= 40:  # 检查呼吸率是否在正常范围内（10-40 BPM）
                    self.br_values.append(avg_br)  # 添加到呼吸率列表
                else:
                    # 如果超出范围，使用默认值或最后一个有效值
                    if self.br_values:  # 如果列表不为空
                        self.br_values.append(0)  # 使用最后一个值
                    else:
                        self.br_values.append(0)  # 使用默认值20
                
                if 40 <= avg_hr <= 200:  # 检查心率是否在正常范围内（40-200 BPM）
                    self.hr_values.append(avg_hr)  # 添加到心率列表
                else:
                    # 如果超出范围，使用默认值或最后一个有效值
                    if self.hr_values:  # 如果列表不为空
                        self.hr_values.append(0)  # 使用最后一个值
                    else:
                        self.hr_values.append(0)  # 使用默认值80
                
                self.point_count += 1  # 增加数据点计数
                
                # 限制数据点数量为37个（对应6分钟滚动窗口）
                # max_points = 37  # 最大显示37个数据点
                # if len(self.br_values) > max_points:  # 如果呼吸率数据点超过最大值
                #     self.br_values = self.br_values[-max_points:]  # 保留最后31个点
                # if len(self.hr_values) > max_points:  # 如果心率数据点超过最大值
                #     self.hr_values = self.hr_values[-max_points:]  # 保留最后31个点
                
                # 确保三个数组长度一致，计算时间点数组
                self.num_points = len(self.br_values)  # 当前数据点数量
                if self.num_points >= 1:  # 如果有多个数据点
                    self.time_points = [(i-1) / 6 for i in range(self.num_points)]
                else:
                    self.time_points = [0]  # 只有一个点时，时间为0
                
                # 记录日志信息
                with open(self.log_file, 'a') as f:
                    f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Raw BR: {self.BR}, Filtered avg_br: {avg_br:.2f}\n")
                    f.write(f"Raw HR: {self.HR}, Filtered avg_hr: {avg_hr:.2f}\n")
                    f.write("="*50 + "\n")
                
                # 格式化显示文本
                br_text = f"{self.br_values[-1]:.1f}"  # 呼吸率文本（保留1位小数）
                hr_text = f"{self.hr_values[-1]:.1f}"  # 心率文本（保留1位小数）
                
                # 只有当有足够数据点时才更新图表

                self.br_curve.setData(self.time_points, self.br_values)  # 更新呼吸率曲线数据
                self.hr_curve.setData(self.time_points, self.hr_values)  # 更新心率曲线数据
                
                

                self.TimeEnd = (self.num_points-2)/6
                if self.TimeEnd >=5:
                    self.TimeEnd = ceil(self.TimeEnd)
                    major_ticks = [(i, str(i)) for i in range(self.TimeEnd-5,self.TimeEnd+3)]
                    minor_ticks = [(i/6, '') for i in range((self.TimeEnd-5)*6,(self.TimeEnd+2)*6) if i % 6 != 0]
                    
                    self.br_plot.getAxis('bottom').setTicks([major_ticks, minor_ticks])
                    self.br_plot.setXRange(self.TimeEnd-5,self.TimeEnd+2, padding=0.01)
                    self.hr_plot.getAxis('bottom').setTicks([major_ticks, minor_ticks])
                    self.hr_plot.setXRange(self.TimeEnd-5,self.TimeEnd+2, padding=0.01)
                
                # 无论是否有足够数据，都要更新当前值标签，确保实时显示
                self.br_value_label.setText(br_text)  # 更新呼吸率文本
                self.hr_value_label.setText(hr_text)  # 更新心率文本
                
                self.recorded_frames = self.recorded_frames[-824:]  # 只保留后824个点
                # self.recorded_frames = self.recorded_frames[-1004:]  # 只保留后824个点
                
                print(f"Update one point {self.num_points}")
            
        except Exception as e:
            print(f"Error in process_frames: {e}")
            print(f"recorded_frames length: {len(self.recorded_frames)}")
            if len(self.recorded_frames) > 0:
                print(f"First frame shape: {np.array(self.recorded_frames[0]).shape}")
            # 清空有问题的数据，避免重复处理
            self.recorded_frames = []
            self.progress_bar.setValue(0)
            # 显示默认值
            self.br_value_label.setText("--")
            self.hr_value_label.setText("--")
        
    def clear_logs(self):
        """
        删除 logs 目录下所有日志文件
        """
        import os
        import shutil
        log_dir = "logs"
        if not os.path.exists(log_dir):
            return
        for fname in os.listdir(log_dir):
            fpath = os.path.join(log_dir, fname)
            if os.path.isfile(fpath):
                os.remove(fpath)  # 删除文件
        # 弹窗提示
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, "提示", "所有日志文件已删除！")

    def closeEvent(self, event):
        """
        窗口关闭事件处理
        确保在关闭窗口时正确停止数据采集和清理资源
        """
        self.stop_acquisition()  # 停止数据采集
        event.accept()  # 接受关闭事件

def main():
    """
    主函数 - 程序入口点
    创建QApplication实例并启动GUI界面
    """
    app = QApplication(sys.argv)  # 创建QApplication实例
    app.setApplicationName("生命体征监测系统")  # 设置应用程序名称
    app.setOrganizationName("ASTRI")  # 设置组织名称
    
    # 创建并显示主窗口
    window = VitalSignsGUI()  # 创建主窗口实例
    window.show()  # 显示窗口
    
    # 启动应用程序事件循环
    sys.exit(app.exec_())  # 进入应用程序主循环，直到退出

# 程序入口点
if __name__ == "__main__":
    main()  # 调用主函数
