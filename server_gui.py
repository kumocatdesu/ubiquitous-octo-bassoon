import sys
import socket
import threading
import json
import time
from flask import Flask, jsonify
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel,
    QTextEdit, QPushButton, QScrollArea, QGridLayout, QMessageBox
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal

# 注文データを保存する場所
orders_data = {}

# PyQt6のシグナルを使ってスレッドからメインスレッドにデータを送る
class OrderSignal(QObject):
    received = pyqtSignal(str)

# --- 親機（ソケット通信サーバー）の設定 ---
HOST_SOCKET = '0.0.0.0'
PORT_SOCKET = 65432

# --- 親機（Webサーバー）の設定 ---
app = Flask(__name__)
HOST_WEB = '0.0.0.0'
PORT_WEB = 5000

# スレッドからメインGUIにデータを送るためのシグナルインスタンス
order_signal = OrderSignal()

def handle_socket_client(conn, addr):
    """子機からの接続を処理するスレッド関数"""
    print(f"ソケット子機が接続しました: {addr}")
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            
            json_data = data.decode('utf-8')
            message = json.loads(json_data)
            
            message_type = message.get("type")
            
            if message_type == "order":
                table_number = message.get("table")
                items = message.get("items", [])
                
                if table_number and items:
                    if table_number not in orders_data:
                        orders_data[table_number] = []
                    
                    for item, count in items:
                        for _ in range(count):
                            orders_data[table_number].append(item)
                    
                    # GUIに通知
                    display_message = f"注文受信 - テーブル: {table_number}, 注文内容: {items}"
                    order_signal.received.emit(display_message)

                    # 受信確認を子機に返す
                    response = {"status": "success", "message": "注文を受け付けました"}
                    conn.sendall(json.dumps(response).encode('utf-8'))
            
            elif message_type == "inquiry":
                print(f"ソケット経由で問い合わせを受信: {addr}")
                response = {"status": "success", "orders": orders_data}
                conn.sendall(json.dumps(response).encode('utf-8'))

    except (socket.error, json.JSONDecodeError) as e:
        print(f"ソケット通信エラー: {e}")
    finally:
        conn.close()
        print(f"子機 {addr} が切断されました。")

def start_socket_server():
    """ソケットサーバーを起動し、接続を待機する"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST_SOCKET, PORT_SOCKET))
        s.listen()
        order_signal.received.emit(f"✅ ソケットサーバー起動中 (ポート: {PORT_SOCKET})")
        while True:
            conn, addr = s.accept()
            client_thread = threading.Thread(target=handle_socket_client, args=(conn, addr))
            client_thread.daemon = True
            client_thread.start()

# --- Webサーバーのルート設定 ---
@app.route('/order_status')
def order_status():
    """現在の注文状況をJSONで返す"""
    return jsonify(orders_data)

def start_web_server():
    """Webサーバーを別スレッドで起動する"""
    order_signal.received.emit(f"✅ Webサーバー起動中 (ポート: {PORT_WEB})")
    app.run(host=HOST_WEB, port=PORT_WEB)


class ServerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("居酒屋Handyアプリ（親機）")
        self.setFixedSize(600, 400)

        self.init_ui()
        
        # 受信シグナルとGUI更新関数を接続
        order_signal.received.connect(self.update_log_display)

        # サーバーをスレッドで起動
        socket_thread = threading.Thread(target=start_socket_server)
        socket_thread.daemon = True
        socket_thread.start()

        web_thread = threading.Thread(target=start_web_server)
        web_thread.daemon = True
        web_thread.start()

    def init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        title_label = QLabel("居酒屋Handy 親機システム")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        main_layout.addWidget(title_label)

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        main_layout.addWidget(self.log_display)

        self.order_status_button = QPushButton("現在の注文状況を表示")
        self.order_status_button.setStyleSheet("background-color: #2196F3; color: white; font-size: 16px; padding: 10px;")
        self.order_status_button.clicked.connect(self.show_current_orders)
        main_layout.addWidget(self.order_status_button)

    def update_log_display(self, message):
        """受信したメッセージをログに追記する"""
        self.log_display.append(message)

    def show_current_orders(self):
        """現在の注文状況をメッセージボックスで表示する"""
        if not orders_data:
            QMessageBox.information(self, "注文状況", "現在、注文はありません。")
            return

        status_text = "--- 現在の注文状況 ---\n"
        for table, items in orders_data.items():
            status_text += f"\n【テーブル {table}】\n"
            item_counts = {}
            for item in items:
                item_counts[item] = item_counts.get(item, 0) + 1
            for item, count in item_counts.items():
                status_text += f" - {item} x{count}\n"
        
        QMessageBox.information(self, "注文状況", status_text)


if __name__ == '__main__':
    app_qt = QApplication(sys.argv)
    server_app = ServerApp()
    server_app.show()
    sys.exit(app_qt.exec())