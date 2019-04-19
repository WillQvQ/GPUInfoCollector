from flask_sqlalchemy import SQLAlchemy
from flask_script import Manager
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask import Flask, request, render_template, send_from_directory
import os
import json
import datetime
import time

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = '1qa2dzc12edcd1f8zschew211'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://' + os.environ.get('MYSQL_USER') + ':' + \
                                        os.environ.get('MYSQL_PASSWORD') + '@localhost:3306/nvidia'
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

bootstrap = Bootstrap(app)
moment = Moment(app)
db = SQLAlchemy(app)
manager = Manager(app)


class Server(db.Model):
    __tablename__ = "server"
    ip = db.Column(db.String(20), primary_key=True)
    pid = db.Column(db.Integer)
    last_report = db.Column(db.DateTime)


class Card(db.Model):
    __tablename__ = 'card'
    uuid = db.Column(db.String(50), primary_key=True)
    ip = db.Column(db.String(20))
    id = db.Column(db.Integer)
    gpu_temp_max_threshold = db.Column(db.Integer)
    gpu_temp_slow_threshold = db.Column(db.Integer)
    #
    last_updated = db.Column(db.DateTime)
    last_used = db.Column(db.DateTime)
    username = db.Column(db.String(20))
    gpu_temp = db.Column(db.Integer)
    fan_speed = db.Column(db.Integer)
    memory_util = db.Column(db.Integer)
    gpu_util = db.Column(db.Integer)
    encoder_util = db.Column(db.Integer)
    decoder_util = db.Column(db.Integer)
    
    def __repr__(self):
        return "%s<%d> max:%d℃ slow:%d℃" % (
            self.ip, self.id, self.gpu_temp_max_threshold, self.gpu_temp_slow_threshold)


class Info(db.Model):
    __tablename__ = 'info'
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(50))
    time = db.Column(db.DateTime)
    username = db.Column(db.String(20))
    gpu_temp = db.Column(db.Integer)
    fan_speed = db.Column(db.Integer)
    memory_util = db.Column(db.Integer)
    gpu_util = db.Column(db.Integer)
    encoder_util = db.Column(db.Integer)
    decoder_util = db.Column(db.Integer)
    
    def __repr__(self):
        return "%s %d" % (self.time, self.gpu_util)


class User(db.Model):
    __tablename__ = 'user'
    username = db.Column(db.String(20), primary_key=True)
    recent_time = db.Column(db.Integer)
    total_time = db.Column(db.Integer)


@app.shell_context_processor
def make_shell_context():
    return dict(app=app, db=db, Info=Info, Card=Card)


@app.route('/post', methods=['POST'])
def post_info():
    ip = request.remote_addr
    data = json.loads(request.data)
    server = Server.query.filter_by(ip=ip).first()
    if server is None:
        server = Server(ip=ip, last_report=datetime.datetime.now())
    server.last_report = datetime.datetime.now()
    db.session.add(server)
    db.session.commit()
    for d in data:
        if isinstance(d, dict):
            if 'uuid' in d and 'ip' in d:
                info = Info()
                info.uuid = d['uuid']
                info.time = datetime.datetime.now()
                info.ip = d['ip'] if d['ip'] != "0.0.0.0" else ip
                info.username = d['username'] if 'username' in d else ""
                info.gpu_util = int(d['gpu_util']) if 'gpu_util' in d else -1
                info.gpu_temp = int(d['gpu_temp']) if 'gpu_temp' in d else -1
                info.fan_speed = int(d['fan_speed']) if ('fan_speed' in d and d['fan_speed'] != 'Unknown') else -1
                info.memory_util = int(d['memory_util']) if 'memory_util' in d else -1
                info.decoder_util = int(d['decoder_util']) if 'decoder_util' in d else -1
                info.encoder_util = int(d['encoder_util']) if 'encoder_util' in d else -1
                card = Card.query.filter_by(uuid=info.uuid).first()
                if card is None:
                    card = Card(uuid=info.uuid, ip=info.ip, id=d["id"],
                                last_used=datetime.datetime.now() - datetime.timedelta(days=300))
                    card.gpu_temp_max_threshold = d["gpu_temp_max_threshold"] if "gpu_temp_max_threshold" in d else -1
                    card.gpu_temp_slow_threshold = d[
                        "gpu_temp_slow_threshold"] if "gpu_temp_slow_threshold" in d else -1
                    server = Server.query.filter_by(ip=info.ip).first()
                    if server is None:
                        server = Server(ip=info.ip, last_report=datetime.datetime.now())
                        db.session.add(server)
                        db.session.commit()
                card.id = d["id"]
                card.gpu_temp = info.gpu_temp
                card.fan_speed = info.fan_speed
                card.gpu_util = info.gpu_util
                card.memory_util = info.memory_util
                card.encoder_util = info.encoder_util
                card.decoder_util = info.decoder_util
                if info.gpu_util > 10 or info.memory_util > 5:
                    card.last_used = datetime.datetime.now()
                    card.username = info.username
                elif datetime.datetime.now() - card.last_used > datetime.timedelta(hours=8):
                    card.username = ""
                user = User.query.filter_by(username=info.username, ).first()
                if user is None:
                    user = User(username=info.username, recent_time=0, total_time=0)
                if card.last_updated is None:
                    card.last_updated = datetime.datetime.now()
                user.total_time += (datetime.datetime.now() - card.last_updated).seconds
                card.last_updated = datetime.datetime.now()
                db.session.add(user)
                db.session.add(info)
                db.session.add(card)
            db.session.add(server)
            db.session.commit()
    return "Get info!"


@app.route('/err', methods=['POST'])
def err_info():
    data = json.loads(request.data)
    ip = request.remote_addr
    server = Server.query.filter_by(ip=ip).first()
    if server is None:
        server = Server(ip=ip, last_report=datetime.datetime.now())
    server.last_report = datetime.datetime.now()
    db.session.add(server)
    db.session.commit()
    print(data)
    return "Get err!"


@app.route('/', methods=['GET'])
def index():
    out = []
    servers = Server.query.all()
    for each in servers:
        delta_time = datetime.datetime.now() - each.last_report
        if delta_time.seconds // 60 > 0:
            if delta_time.seconds // 60 > 29:
                state = 2
            elif delta_time.seconds // 60 > 4:
                state = 1
            else:
                state = 0
            last_updated = str(delta_time.seconds // 60) + "m" + "%02ds ago" % (delta_time.seconds % 60)
        else:
            state = 0
            last_updated = "%ds ago" % (delta_time.seconds % 60)
        server = {
            "ip": each.ip,
            "last_updated": last_updated,
            "state": state,
            "cards": [card.uuid for card in Card.query.filter_by(ip=each.ip).order_by(Card.id.asc()).all()]
        }
        out.append(server)
    out.sort(key=lambda x: x["ip"])
    last = {}
    cards = Card.query.all()
    for each in cards:
        if each.uuid == "GPU-LAST-START":
            continue
        delta_time = datetime.datetime.now() - each.last_used
        if delta_time > datetime.timedelta(days=300):
            last[each.uuid] = "--"
        elif delta_time > datetime.timedelta(hours=8):
            last[each.uuid] = ">8h"
        elif delta_time < datetime.timedelta(minutes=5):
            last[each.uuid] = "in use"
        else:
            last[each.uuid] = str((delta_time.seconds // 60) % 60) + "m"
            if delta_time.seconds // 3600 > 0:
                last[each.uuid] = str(delta_time.seconds // 3600) + "h" + last[each.uuid]
    users = User.query.all()
    recent = []
    total = []
    card = Card.query.filter_by(uuid="GPU-LAST-START").first()
    last_updated = card.last_updated + datetime.timedelta(hours=12)
    for user in users:
        if len(user.username) > 1:
            if user.total_time - user.recent_time > 600:
                recent.append([user.username, int((user.total_time - user.recent_time) / 3600 * 100) / 100])
            total.append([user.username, int(user.total_time / 3600 * 100) / 100])
    recent.sort(key=lambda x: -x[1])
    total.sort(key=lambda x: -x[1])
    return render_template('index.html', servers=out, last=last, recent=recent, last_updated=last_updated,
                           total=total, cards={each.uuid: each for each in cards})


def delete():
    infos = Info.query.filter(Info.time < datetime.datetime.now() - datetime.timedelta(hours=23)).all()
    for info in infos:
        db.session.delete(info)
    db.session.commit()


@app.route('/detail/<uuid>', methods=['GET'])
def detail(uuid):
    delete()
    card = Card.query.filter_by(uuid=uuid).first()
    if card is None:
        return "NOT FOUND"
    info = Info.query.filter_by(uuid=uuid).order_by(Info.time.asc()).all()[::5]
    now = datetime.datetime.now()
    memory_util = []
    gpu_util = []
    times = []
    for i in range(0, len(info), 5):
        memory = [each.memory_util for each in info[i:i + 5]]
        memory_util.append(sum(memory) / len(memory))
        gpu = [each.gpu_util for each in info[i:i + 5]]
        gpu_util.append(sum(gpu) / len(gpu))
        times.append(round((now - info[i].time).seconds / 3600, 1))
    return render_template('detail.html', card=card, time=times, gpu_util=gpu_util, memory_util=memory_util)


@app.route('/reporter', methods=['GET'])
def reporter():
    return send_from_directory(app.root_path, "reporter.py")


@app.errorhandler(404)
def page_not_found(_):
    return render_template('404.html'), 404


@manager.command
def init():
    db.drop_all()
    db.create_all()


@manager.command
def run():
    app.run(port=8997, host='0.0.0.0', debug=False)


def update_rank_list():
    card = Card.query.filter_by(uuid="GPU-LAST-START").first()
    card.last_updated = datetime.datetime.now()
    users = User.query.all()
    for user in users:
        user.recent_time = user.total_time
        db.session.add(user)
    db.session.add(card)
    db.session.commit()


@manager.command
def clean():
    while 1:
        delete()
        update_rank_list()
        print(datetime.datetime.now() + datetime.timedelta(hours=13))
        time.sleep(3600 * 24)


if __name__ == '__main__':
    manager.run()
