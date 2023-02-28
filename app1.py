import sqlalchemy
from fastapi import requests
from flask import Flask, request, jsonify
import sqlalchemy as sql
from sqlalchemy.ext import declarative
from sqlalchemy.orm import sessionmaker
import requests
import hashlib
import base64
import time
from bs4 import BeautifulSoup

'''
西二python组第一轮后端考核：
非完整版，跨域功能没有完全实现，
'''
app = Flask(__name__)
engine = sqlalchemy.create_engine('mysql+pymysql://root:070112@localhost/users?charset=utf8mb4')
BaseModel = declarative.declarative_base()
session = sessionmaker(bind=engine)()


# 跨域操作
class MyMiddle:
    def process_response(self, request, response):
        response['Access-Control-Allow-Origin'] = '*'
        if request.method == "OPTIONS":
            # 可以加*
            response["Access-Control-Allow-Headers"] = "Content-Type"
            response["Access-Control-Allow-Headers"] = "authorization"

        return response


class User(BaseModel):
    __tablename__ = 'users'  # 表名
    id = sql.Column(sql.Integer, primary_key=True)  # id为唯一主键
    username = sql.Column(sql.String(100))  # 用户名
    password = sql.Column(sql.String(18))  # 密码


class Search(BaseModel):
    __tablename__ = 'search'
    name = sql.Column(sql.String(10))  # 歌名
    artist = sql.Column(sql.String(10))  # 歌手
    album = sql.Column(sql.String(10))  # 专辑
    duration = sql.Column(sql.String(10))  # 歌曲时长
    rid = sql.column(sql.String(10))


class History(BaseModel):
    __tablename__ = 'music_history'  # 表名
    id = sql.Column(sql.Integer, primary_key=True)
    type = sql.Column(sql.Integer)
    name = sql.Column(sql.String(10))  # 歌名
    artist = sql.Column(sql.String(10))  # 歌手
    album = sql.Column(sql.String(10))  # 专辑
    duration = sql.Column(sql.String(10))  # 歌曲时长
    list = sql.Column(sql.String(1000))  # 历史记录的id列表
    fav = sql.Column(sql.Integer)  # 0为取消收藏，1为收藏


class Token_hander():
    def __init__(self, out_time):
        self.out_time = out_time
        self.time = self.timer
        pass

    def timer(self):
        return time.time()

    def hax(self, str):
        """
        摘要算法加密
        :param str: 待加密字符串
        :return: 加密后的字符串
        """
        if not isinstance(str, bytes):  # 如果传入不是bytes类型，则转为bytes类型
            try:
                str = bytes(str, encoding="utf8")
            except BaseException as ex:
                raise ValueError("'%s'不可被转换为bytes类型" % str)

        md5 = hashlib.md5()
        md5.update("070112".encode(encoding='utf-8'))
        md5.update(str)
        md5.update("070112".encode(encoding='utf-8'))
        return md5.hexdigest()

    def build_token(self, message):
        """
        hax_message: 待加密字符串内容  格式： '当前时间戳：message：过期时间戳'
        :param message: 需要生成token的字符串
        :return: token
        """
        hax_message = "%s:%s:%s" % (str(self.time()), message, str(float(self.time()) + float(self.out_time)))
        hax_res = self.hax(hax_message)
        token = base64.urlsafe_b64encode(("%s:%s" % (hax_message, hax_res)).encode(encoding='utf-8'))
        return token.decode("utf-8")

    def check_token(self, token):
        """

        :param token: 待检验的token
        :return: False   or  new token
        """
        try:
            hax_res = base64.urlsafe_b64decode(token.encode("utf8")).decode("utf-8")
            message_list = hax_res.split(":")
            md5 = message_list.pop(-1)
            message = ':'.join(message_list)
            if md5 != self.hax(message):
                # 加密内容如果与加密后的结果不符即token不合法
                return False
            else:
                if self.time() - float(message_list.pop(-1)) > 0:
                    # 超时返回False
                    return False
                else:
                    # token验证成功返回新的token
                    return self.build_token(message_list.pop(-1))
        except BaseException as ex:
            # 有异常表明验证失败或者传入参数不合法
            return False


@app.route('/user/login', methods=['post'])
def login():
    try:
        username = request.json.get("username").strip()
        password = request.json.get("password").strip()
        token_hander = Token_hander(2000)
        password = token_hander.hax(password)
        result = session.query(User).filter(User.username == username).values(password)
        user_id = session.query(User).filter(User.username == username).values(id)
        session.commit()
        token = token_hander.build_token(username)
        if password == result:
            return jsonify({
                "code": 200, "message": "success", "data": {
                    "id": user_id, "username": username, "token": token
                }
            })

    except Exception as e:
        return jsonify({
            "code": 200, "msg": e
        })


@app.route('/user', methods=['post'])
def register():
    try:
        username = request.json.get("username").strip()
        password = request.json.get("password").strip()
        checkPassword = request.json.get('checkPassword').strip()
        token_hander = Token_hander(2000)
        if password == checkPassword:
            password = token_hander.hax(password)
            session.add(User(id=1, username=username, password=password))
            session.commit()
            return jsonify({
                "code": 200, "message": "success", "data": {
                    "id": id, "username": username
                }
            })

        else:
            return jsonify({
                "code": 200, "msg": "两次密码不一致"
            })
    except Exception as e:
        return jsonify({
            "code": 200, "msg": e
        })


@app.route('/search?text=<str:text>', methods=['get'])
def search(pages):
    header = request.json.get("Authorization").strip()
    text = request.json.get("text").strip()
    url = "http: //www.kuwo.cn/search/list?key=" + text
    resp = requests.get(url, headers=header)
    cnt = 1
    datalist = resp.json()['data']['list']
    data_list = []
    token_hander = Token_hander(2000)
    if token_hander.check_token(header):
        for i in datalist:
            name = i['name'].replace('&nbsp;', ' ')
            i['name'] = name
            artist = i['artist'].replace('&nbsp;', ' ')
            album = i['album'].replace('&nbsp;', ' ')
            duration = i['duration'].replace('&nbsp;', ' ')
            rid = i['rid'].replace('&nbsp;', ' ')
            i['artist'] = artist
            i['seq'] = cnt
            i['duration'] = duration
            i['rid'] = rid
            cnt += 1
            data = {
                "name": i[name],
                "artist": i[artist],
                "album": i[album],
                "duration": i[duration],
                "rid": i[rid]
            }
            data_list.append(data)
        # 分页
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        paginate = User.query.order_by('text').paginate(page, per_page, error_out=False)
        dxtd = paginate.items
        dxtd.reverse()
        return jsonify({
            "code": 200, "message": "success", "data": {
                "list": {
                    data_list
                }
            }
        })


@app.route('/search/download/:<str:rid>', methods=['get'])
def download():
    rid = request.json.get('rid').strip()
    header = request.json.get("Authorization").strip()
    token_hander = Token_hander(2000)
    if token_hander.check_token(header):
        try:
            url = 'https://www.kuwo.cn/play_detail/%s' % rid
            data = request.get(url).content
            with open("{}.mp3".format(rid), "wb") as file_object:  # wb表示以二进制形式写入
                # 写入数据
                file_object.write(data)
            return file_object
        except Exception as e:
            return jsonify({
                "code": 400, "message": e
            })


@app.route('/user/history', methods=['delete'])
def delete():
    header = request.json.get("Authorization").strip()
    token_hander = Token_hander(2000)
    if token_hander.check_token(header):
        h_type = request.json.get('type').strip()
        h_id = request.json.get('id').strip()
        h_list = request.json.get('list').strip()
        token_hander = Token_hander(2000)
        if token_hander.check_token(header):
            try:
                if h_type == '0':
                    session.query(History).filter(History.id == id).delete()
                    session.commit()
                else:
                    for i in h_list:
                        session.query(History).filter(History.id == i).delete()
                        session.commit()
                return jsonify({
                    "code": 200, "message": "success"
                })
            except Exception as e:
                return jsonify({
                    "code": 200, "message": e
                })


@app.route('/user/history?page=<int:page>', methods=['get'])
def get_history():
    header = request.json.get("Authorization").strip()
    token_hander = Token_hander(2000)
    if token_hander.check_token(header):
        page = request.json.get('page').strip()
        try:
            url = 'http://127.0.0.1:8000/user/history?page=' + page
            req = request.get(url)
            req.encodeing = "utf-8"
            html = req.text
            soup = BeautifulSoup(req.text, features="html.parser")
            name = soup.find_all("div", class_="name")
            artist = soup.find_all("div", class_="artist")
            album = soup.find_all("div", class_="album")
            duration = soup.find_all("div", class_="duration")
            fav = soup.find_all("div", class_="fav")
            rid = soup.find_all("div", class_="rid")
            id = soup.find_all("div", class_="id")
            data = []
            for i in range(0, 10):
                lit = {
                    "name": name[i], "artist": artist[i], "album": album[i], "duration": duration[i], "fav": fav[i],
                    "rid": rid[i], "id": id[i]
                }
                data.append(lit)

            return jsonify({
                "code": 200, "message": "success", "data": {
                    "list": {
                        data
                    }
                }
            })
        except Exception as e:
            return jsonify({
                "code": 200, "message": e
            })


@app.route('/user/history/lc', methods=['put'])
def update_history():
    header = request.json.get("Authorization").strip()
    token_hander = Token_hander(2000)
    if token_hander.check_token(header):
        try:
            h_id = request.json.get('id').strip()
            fav = request.json.get('fav').strip()
            session.query(History).filter(History.id == h_id).update({History.fav: fav})
            data = session.query(History).filter(History.id == h_id).one()
            session.commit()
            return jsonify({
                "code": 200, "message": "success", "data": {
                    "name": data.name, "artist": data.artist, "album": data.album,
                    "duration": data.duration, "rid": data.duration
                }

            })

        except Exception as e:
            return jsonify({
                "code": 200, "message": e
            })


if __name__ == '__main__':
    app.run()
