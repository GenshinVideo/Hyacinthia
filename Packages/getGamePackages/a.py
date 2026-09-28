import os
import json
import glob
import hashlib

def process_and_deduplicate_jsons():
    # フォルダ内の日付付きのJSONファイルを取得
    json_files = sorted(glob.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]_*.json"))
    
    if not json_files:
        print("❌ 対象となる日付付きのJSONファイルが見つかりません。")
        return

    print(f"🔍 {len(json_files)} 個のJSONファイルを検出しました。文字コードを補正して処理を開始します。")

    last_file_hash = None
    last_file_name = None

    for file_path in json_files:
        try:
            # 1. PowerShellの文字コード（UTF-16 LE等）に対応するため、適切なエンコーディングで読み込み
            # まずはutf-16で試み、失敗したらutf-8（sig付き含む）で読み込む
            try:
                with open(file_path, 'r', encoding='utf-16') as f:
                    content = f.read()
            except (UnicodeDecodeError, Exception):
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    content = f.read()

            # 2. 不要なコメント行（//）を除去して綺麗なJSON文字列にする
            lines = [line for line in content.splitlines() if not line.strip().startswith("//")]
            clean_content = "\n".join(lines).strip()
            
            if not clean_content:
                continue
                
            try:
                js_data = json.loads(clean_content)
            except json.JSONDecodeError as je:
                print(f"⚠️ {file_path} のパースに失敗しました（JSONの構文エラー: {je}）。スキップします。")
                continue

            # 3. 本家形式の入れ子構造（"data" の中に元のJSONを入れる）を作成
            if "retcode" not in js_data:
                final_structure = {
                    "retcode": 0,
                    "message": "OK",
                    "data": js_data
                }
            else:
                final_structure = js_data

            # 4. 本家と同じように余分な空白・改行を一切排除して1行に圧縮
            compressed_json = json.dumps(final_structure, separators=(',', ':'), ensure_ascii=False)

            # 5. 一つ前の有効なファイルと「完全に同じ」かMD5ハッシュで比較確認
            current_hash = hashlib.md5(compressed_json.encode('utf-8')).hexdigest()

            if last_file_hash == current_hash:
                # まったく同じデータだった場合
                print(f"🗑️  [重複判明] {file_path} は、1つ前の {last_file_name} と中身が完全に一致したため削除します。")
                os.remove(file_path)
            else:
                # 違いがあった場合、本家と同じ純粋な UTF-8 (BOMなし) で上書き保存
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(compressed_json)
                print(f"✨ [更新アリ] {file_path} を本家形式に整形・1行圧縮しました。")
                
                # 次の比較用にハッシュとファイル名を保存
                last_file_hash = current_hash
                last_file_name = file_path

        except Exception as e:
            print(f"❌ {file_path} の処理中に予期せぬエラーが発生しました: {e}")

    print("\n✅ すべてのJSONファイルの整形・重複チェックが完了しました！")

if __name__ == "__main__":
    process_and_deduplicate_jsons()
