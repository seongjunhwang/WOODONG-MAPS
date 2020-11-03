from pymongo import MongoClient
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

client = MongoClient('localhost', 27017)
db = client.woodong


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/create')
def contents():
    return render_template('contentCreate.html')


@app.route('/api/contents', methods=['POST'])
def create_contents():
    lat = request.form['lat']
    lng = request.form['lng']
    image = request.form['image']
    title = request.form['title']
    desc = request.form['desc']
    uid = "test_user1"

    db.contents.insert_one(
        {
            'latitude': lat,
            'longitude': lng,
            'image': image,
            'title': title,
            'desc': desc,
            'uid': uid
        }
    )

    return jsonify({'result': 'success', 'msg': '게시글 등록이 완료되었습니다.'})


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
