import hashlib
import datetime
import jwt
from pymongo import MongoClient
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import uuid
import json
import requests

app = Flask(__name__)

client = MongoClient('localhost', 27017)
db = client.woodong

SECRET_KEY = 'apple'


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register')
def register():
    return render_template('register.html')


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/content')
def content():
    return render_template('content.html')


@app.route('/create')
def contents():
    return render_template('contentCreate.html')


# [회원가입 API]
# id, pw 받아서, mongoDB에 저장합니다.
# 저장하기 전에, pw를 sha256 방법(=단방향 암호화. 풀어볼 수 없음)으로 암호화해서 저장합니다.


@app.route('/api/users', methods=['POST'])
def api_users():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']
    nickname_receive = request.form['nickname_give']

    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    db.users.insert_one(
        {'id': id_receive, 'pw': pw_hash, 'nick': nickname_receive})

    return jsonify({'result': 'success'})

# [로그인 API]
# id, pw를 받아서 맞춰보고, 토큰을 만들어 발급합니다.


@app.route('/api/login', methods=['POST'])
def api_login():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']

    # 회원가입 때와 같은 방법으로 pw를 암호화합니다.
    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    # id, 암호화된pw을 가지고 해당 유저를 찾습니다.
    result = db.users.find_one({'id': id_receive, 'pw': pw_hash})

    # 찾으면 JWT 토큰을 만들어 발급합니다.
    if result is not None:
        # JWT 토큰에는, payload와 시크릿키가 필요합니다.
        # 시크릿키가 있어야 토큰을 디코딩(=풀기) 해서 payload 값을 볼 수 있습니다.
        # 아래에선 id와 exp를 담았습니다. 즉, JWT 토큰을 풀면 유저ID 값을 알 수 있습니다.
        # exp에는 만료시간을 넣어줍니다. 만료시간이 지나면, 시크릿키로 토큰을 풀 때 만료되었다고 에러가 납니다.
        payload = {
            'id': id_receive,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=30000)

        }
        token = jwt.encode(payload, SECRET_KEY,
                           algorithm='HS256').decode('utf-8')

        # token을 줍니다.
        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})

# [유저 정보 확인 API]
# 로그인된 유저만 call 할 수 있는 API입니다.
# 유효한 토큰을 줘야 올바른 결과를 얻어갈 수 있습니다.
# (그렇지 않으면 남의 장바구니라든가, 정보를 누구나 볼 수 있겠죠?)


@app.route('/api/nick', methods=['GET'])
def api_valid():
    # 토큰을 주고 받을 때는, 주로 header에 저장해서 넘겨주는 경우가 많습니다.
    # header로 넘겨주는 경우, 아래와 같이 받을 수 있습니다.
    token_receive = request.headers['token_give']

    # try / catch 문?
    # try 아래를 실행했다가, 에러가 있으면 except 구분으로 가란 얘기입니다.

    try:
        # token을 시크릿키로 디코딩합니다.
        # 보실 수 있도록 payload를 print 해두었습니다. 우리가 로그인 시 넣은 그 payload와 같은 것이 나옵니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
        # 여기에선 그 예로 닉네임을 보내주겠습니다.
        userinfo = db.users.find_one({'id': payload['id']}, {'_id': 0})
        return jsonify({'result': 'success', 'nickname': userinfo['nick']})
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})


@app.route('/api/contents', methods=['POST'])
def api_create_contents():
    lat = request.form['lat']
    lng = request.form['lng']
    image = request.form['image']
    title = request.form['title']
    desc = request.form['desc']
    token = request.form['token']
    createdtime = request.form['createdtime']
    payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    userid = db.users.find_one({'id': payload['id']}, {'_id': 0, 'id': 1})
    usernick = db.users.find_one({'id': payload['id']}, {'_id': 0, 'nick': 1})
    db.contents.insert_one(
        {
            'contentid': uuid.uuid4().hex[:8],
            'createdtime': createdtime,
            'latitude': lat,
            'longitude': lng,
            'userid': userid['id'],
            'usernick': usernick['nick'],
            'image': image,
            'title': title,
            'desc': desc
        }
    )
    return jsonify({'result': 'success', 'msg': '게시글 등록이 완료되었습니다.'})


@ app.route('/api/contents', methods=['GET'])
def api_read_contents():

    contents = list(db.contents.find(
        {}, {'_id': 0}).sort('createdtime', -1))

    return jsonify({'result': 'success', 'contents_list': contents})


@app.route('/api/coordsToAddress/<coords>', methods=['GET'])
def api_coords_to_address(coords):

    client_id = '5h7phq9a8i'
    client_secret = 'zmXRdAWu3QSyafJEneva4vKY3AXN2TRZdKtrXSU7'

    headers = {
        'X-NCP-APIGW-API-KEY-ID': client_id,
        'X-NCP-APIGW-API-KEY': client_secret
    }

    params = (
        ('request', 'coordsToaddr'),
        ('coords', coords),
        ('sourcecrs', 'epsg:4326'),
        ('output', 'json'),
        ('orders', 'legalcode,admcode'),
    )

    response = requests.get(
        'https://naveropenapi.apigw.ntruss.com/map-reversegeocode/v2/gc', headers=headers, params=params)

    return jsonify({'result': 'success', 'address': response.json()})


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
