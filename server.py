import socket
import threading
import json
from flask import Flask, request, jsonify

# --- 親機（ソケット通信サーバー）の設定 ---
HOST_SOCKET = '0.0.0.0'
PORT_SOCKET = 65432

# --- 親機（Webサーバー）の設定 ---
app = Flask(__name__)
HOST_WEB = '0.0.0.0'
PORT_WEB = 5000

# 注文データを保存する場所（例として辞書を使用）
orders_data = {}
clients = {} # 接続されている子機を管理する辞書

def handle_socket_client(conn, addr):
    """ソケット子機からの接続を処理"""
    print(f"ソケット子機が接続しました: {addr}")
    clients[addr] = conn # 子機を管理リストに追加
    
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
                    
                    print(f"ソケット経由で注文を受信: テーブル {table_number}, 注文内容: {items}")
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
        del clients[addr]
        print(f"子機 {addr} が切断されました。")

def start_socket_server():
    """ソケットサーバーを起動し、接続を待機する"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST_SOCKET, PORT_SOCKET))
        s.listen()
        print(f"ソケットサーバーを起動しました。ポート {PORT_SOCKET} で接続を待機中...")
        while True:
            conn, addr = s.accept()
            client_thread = threading.Thread(target=handle_socket_client, args=(conn, addr))
            client_thread.start()

# --- Webサーバーのルート設定 ---
@app.route('/order_status')
def order_status():
    """現在の注文状況をJSONで返す"""
    return jsonify(orders_data)

if __name__ == '__main__':
    socket_thread = threading.Thread(target=start_socket_server)
    socket_thread.daemon = True
    socket_thread.start()

    app.run(host=HOST_WEB, port=PORT_WEB)