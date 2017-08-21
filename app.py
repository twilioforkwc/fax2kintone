# app.py
from flask import Flask
app = Flask(__name__)

from flask import request
from flask import Response
import datetime
import requests
import uuid
import json
import configparser
import base64

config = configparser.RawConfigParser()
config.read('config.ini')
URL = str(config['KINTONE']['url'])
APP_ID = str(config['KINTONE']['app_id'])
API_TOKEN = str(config['KINTONE']['api_token'])
LOGIN_USER = str(config['KINTONE']['login_user'])
LOGIN_PASS = str(config['KINTONE']['login_pass'])
KNT_PASS = base64.b64encode(str(LOGIN_USER+':'+LOGIN_PASS).encode('utf-8'))  # ログインネーム:パスワード をbase64でエンコード
PASS='./pdf/' #ファイル保存パス

@app.route('/receive', methods=['POST'])
def receive():
    # ホスト名を取得
    host = request.headers['Host']
    xml = '<?xml version="1.0" encoding="UTF-8" ?> '
    xml += '<Response>'
    xml += '    <Receive action="https://'+host+'/received" method="POST" />'
    xml += '</Response>'
    return Response(xml, mimetype='text/xml')

@app.route('/received', methods=['POST'])
def received():
    # ステータスが受信完了
    if (request.form["FaxStatus"] == 'received'):
        # 受信日時（JSTで保存）
        receivedDate = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000+0900")
        # 送信元
        from_ = request.form["From"]
        # PDFをダウンロード
        mediaUrl = request.form["MediaUrl"]
        filename = download_file(mediaUrl)
        # kintoneに保存
        knt=KINTONE()
        resp=knt.UploadToKintone(URL, KNT_PASS, PASS, filename)

        txt=json.loads(resp.text)
        FileKey=txt['fileKey']
        resp=knt.PostToKintone(URL, APP_ID, API_TOKEN, FileKey, receivedDate, from_)
        print(resp.text)

        # kintoneApi(receivedDate, from_, pdf)

    return 'OK'

def download_file(url):
    filename = str(uuid.uuid4())+'.pdf'
    local_filename = PASS+filename
    r = requests.get(url, stream=True)
    with open(local_filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)
                #f.flush() commented by recommendation from J.F.Sebastian
    return filename

class KINTONE:
    def UploadToKintone(self, url, knt_pass, path, filename):
        pdf = open(path + filename, 'rb')
        files={'file':(filename,pdf,'application/pdf')}

        headers = {"X-Cybozu-Authorization": knt_pass , 'X-Requested-With': 'XMLHttpRequest'}
        resp=requests.post(url+"/k/v1/file.json",files=files,headers=headers)

        return resp

    def PostToKintone(self, url, appId, apiToken, filekey, receivedDate, from_):
        record = {
            "receivedDate":{'value': receivedDate},
            "from_":{'value': from_},
            "pdf":{'type':"FILE","value" :[{'fileKey':filekey}]}
            #他のフィールドにデータを挿入する場合は','で区切る
        }
        data = {'app':appId,'record':record}
        headers = {"X-Cybozu-API-Token": apiToken, "Content-Type" : "application/json"}
        resp=requests.post(url+'/k/v1/record.json',json=data,headers=headers)

        return resp




if __name__ == "__main__":
    app.run()
