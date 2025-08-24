import socket
import json
import time

# 親機（サーバー）の設定
HOST = '127.0.0.1'  # 親機のIPアドレスに置き換えてください
PORT = 65432        # 親機と同じポート番号

def start_client():
    """コマンドラインから注文を送信するクライアントを起動します。"""
    print("--- 居酒屋Handyアプリ（CUI版） ---")
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            print(f"✅ 親機 {HOST}:{PORT} に接続しました。")
        except ConnectionRefusedError:
            print("❌ 接続に失敗しました。親機が起動しているか、IPアドレスとポートが正しいか確認してください。")
            return

        while True:
            table_number = input("テーブル番号を入力してください (終了する場合は 'exit'): ")
            if table_number.lower() == 'exit':
                break
                
            item_name = input("注文内容を入力してください (例: 焼き鳥): ")
            if item_name.lower() == 'exit':
                break

            # 注文データを構造化して送信
            order_data = {
                "table": table_number,
                "items": [[item_name, 1]], # 単一アイテムをリスト形式で送信
                "timestamp": int(time.time())
            }

            try:
                json_message = json.dumps(order_data)
                message_bytes = json_message.encode('utf-8')
                s.sendall(message_bytes)
                print(f"📦 注文データを送信しました: {order_data}")

            except socket.error as e:
                print(f"❌ 送信エラーが発生しました: {e}")
                break
                
if __name__ == "__main__":
    start_client()