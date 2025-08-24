import sys
import socket
import json
import time
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QScrollArea, QMessageBox, QGridLayout
)
from PyQt6.QtCore import Qt
from collections import OrderedDict
import pykakasi

# 親機（サーバー）の設定
HOST = '127.0.0.1'  # サーバーのIPアドレス
PORT = 65432        # サーバーのポート

class ClientApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("居酒屋Handyアプリ（子機）")
        self.setFixedSize(360, 640)

        self.kks = pykakasi.kakasi()
        self.menu_dict = self.get_menu_items()
        self.menu_hiragana_dict = self.generate_hiragana_map()

        self.current_order = OrderedDict()
        self.socket = None

        self.init_ui()
        self.connect_to_server()

    def get_menu_items(self):
        categorized_menu = {
            "肉": [("焼き鳥", 180), ("豚バラ串", 180), ("鶏皮串", 150), ("つくね串", 200)],
            "魚": [("刺身三点盛り", 980), ("アジの開き", 650), ("ホッケの塩焼き", 800)],
            "その他": [("枝豆", 280), ("冷奴", 250), ("フライドポテト", 320)],
            "飲み物": [("生ビール", 500), ("レモンサワー", 450), ("ハイボール", 480)],
        }
        return categorized_menu

    def generate_hiragana_map(self):
        hiragana_map = {}
        for _, items in self.menu_dict.items():
            for name, _ in items:
                result = self.kks.convert(name)
                hiragana_map[name] = ''.join([item['hira'] for item in result])
        return hiragana_map

    def init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        self.status_label = QLabel("接続していません。")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: red;")
        main_layout.addWidget(self.status_label)

        table_layout = QHBoxLayout()
        table_layout.addWidget(QLabel("テーブル番号:"))
        self.table_input = QLineEdit()
        self.table_input.setPlaceholderText("例: 1, 2など")
        table_layout.addWidget(self.table_input)
        main_layout.addLayout(table_layout)
        
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("メニュー名を検索 (ひらがな可)")
        self.search_input.textChanged.connect(self.search_menu)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)

        self.menu_scroll_area = QScrollArea()
        self.menu_scroll_area.setWidgetResizable(True)
        self.menu_container = QWidget()
        self.menu_layout = QVBoxLayout(self.menu_container)
        self.menu_scroll_area.setWidget(self.menu_container)
        main_layout.addWidget(self.menu_scroll_area)
        self.populate_menu_buttons(self.menu_dict)

        self.order_label = QLabel("注文リスト:")
        main_layout.addWidget(self.order_label)
        self.ordered_list = QLineEdit()
        self.ordered_list.setReadOnly(True)
        self.ordered_list.setStyleSheet("background-color: #f0f0f0;")
        main_layout.addWidget(self.ordered_list)

        button_layout = QHBoxLayout()
        send_button = QPushButton("注文を送信")
        send_button.setStyleSheet("background-color: #4CAF50; color: white; font-size: 16px; padding: 8px;")
        send_button.clicked.connect(self.send_order)
        button_layout.addWidget(send_button)

        inquiry_button = QPushButton("注文状況を問い合わせ")
        inquiry_button.setStyleSheet("background-color: #2196F3; color: white; font-size: 16px; padding: 8px;")
        inquiry_button.clicked.connect(self.inquire_status)
        button_layout.addWidget(inquiry_button)

        main_layout.addLayout(button_layout)

    def connect_to_server(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((HOST, PORT))
            self.status_label.setText("✅ 親機に接続済み")
            self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: green;")
        except ConnectionRefusedError:
            self.status_label.setText("❌ 接続エラー: 親機が起動していません")
            self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: red;")
            self.socket = None

    def populate_menu_buttons(self, menu_data):
        for i in reversed(range(self.menu_layout.count())):
            widget = self.menu_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        for category, items in menu_data.items():
            category_label = QLabel(category)
            category_label.setStyleSheet("font-weight: bold; font-size: 16px;")
            self.menu_layout.addWidget(category_label)

            grid_layout = QGridLayout()
            self.menu_layout.addLayout(grid_layout)

            for i, (name, price) in enumerate(items):
                button = QPushButton(f"{name} ({price}円)")
                button.clicked.connect(lambda checked, n=name: self.add_to_order_list(n))
                row = i // 2
                col = i % 2
                grid_layout.addWidget(button, row, col)

    def search_menu(self):
        query = self.search_input.text().strip().lower()
        filtered_menu = {}
        if not query:
            self.populate_menu_buttons(self.menu_dict)
            return
        
        for category, items in self.menu_dict.items():
            filtered_items = []
            for name, price in items:
                if query in name.lower() or query in self.menu_hiragana_dict.get(name, ""):
                    filtered_items.append((name, price))
            if filtered_items:
                filtered_menu[category] = filtered_items
        
        self.populate_menu_buttons(filtered_menu)

    def add_to_order_list(self, item_name):
        self.current_order[item_name] = self.current_order.get(item_name, 0) + 1
        self.update_order_display()

    def update_order_display(self):
        display_text = ", ".join([f"{name} x{count}" for name, count in self.current_order.items()])
        self.ordered_list.setText(display_text)

    def send_order(self):
        if self.socket is None:
            QMessageBox.critical(self, "エラー", "サーバーに接続されていません。")
            return

        table_number = self.table_input.text().strip()
        if not table_number:
            QMessageBox.warning(self, "警告", "テーブル番号を入力してください。")
            return
        
        if not self.current_order:
            QMessageBox.warning(self, "警告", "注文する商品がありません。")
            return

        order_data = {
            "type": "order",
            "table": table_number,
            "items": list(self.current_order.items()),
            "timestamp": int(time.time())
        }

        try:
            json_message = json.dumps(order_data)
            self.socket.sendall(json_message.encode('utf-8'))
            
            response_data = self.socket.recv(4096).decode('utf-8')
            response = json.loads(response_data)
            
            if response.get("status") == "success":
                QMessageBox.information(self, "成功", "注文を送信しました！")
            else:
                QMessageBox.critical(self, "エラー", "サーバーからの応答エラー")
            
            self.current_order = OrderedDict()
            self.update_order_display()

        except socket.error as e:
            QMessageBox.critical(self, "送信エラー", f"データの送信中にエラーが発生しました。\n詳細: {e}")
            self.connect_to_server()

    def inquire_status(self):
        if self.socket is None:
            QMessageBox.critical(self, "エラー", "サーバーに接続されていません。")
            return

        inquiry_data = {
            "type": "inquiry",
        }

        try:
            json_message = json.dumps(inquiry_data)
            self.socket.sendall(json_message.encode('utf-8'))
            
            response_data = self.socket.recv(4096).decode('utf-8')
            response = json.loads(response_data)

            if response.get("status") == "success":
                orders = response.get("orders", {})
                status_text = "--- 現在の注文状況 ---\n"
                if not orders:
                    status_text += "現在、注文はありません。"
                else:
                    for table, items in orders.items():
                        status_text += f"\n【テーブル {table}】\n"
                        # 注文された商品をカウント
                        item_counts = {}
                        for item in items:
                            item_counts[item] = item_counts.get(item, 0) + 1
                        for item, count in item_counts.items():
                            status_text += f" - {item} x{count}\n"

                QMessageBox.information(self, "注文状況", status_text)
            else:
                QMessageBox.critical(self, "エラー", "注文状況の取得に失敗しました。")

        except socket.error as e:
            QMessageBox.critical(self, "通信エラー", f"問い合わせ中にエラーが発生しました。\n詳細: {e}")
            self.connect_to_server()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    client_app = ClientApp()
    client_app.show()
    sys.exit(app.exec())