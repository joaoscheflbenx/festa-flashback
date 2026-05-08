from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import json, os, uuid
from datetime import datetime
 
app = Flask(__name__, static_folder='.')
app.secret_key = 'flashback_secret_key_2025'
CORS(app, supports_credentials=True, origins=['http://localhost:5000', 'http://127.0.0.1:5000'])
 
DATA_DIR    = 'data'
UPLOAD_DIR  = 'uploads'
NEWS_FILE   = os.path.join(DATA_DIR, 'news.json')
DJS_FILE    = os.path.join(DATA_DIR, 'djs.json')
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_MB      = 5
ADMIN_USER  = 'admin'
ADMIN_PASS  = 'admin'
 
def load(path):
    if not os.path.exists(path): return []
    with open(path, encoding='utf-8') as f: return json.load(f)
 
def save(path, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
 
def allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT
 
def admin_required():
    if not session.get('admin'):
        return jsonify({'error': 'Não autorizado'}), 403
    return None
 
# ── static ────────────────────────────────────────────────────────────────
@app.route('/')
def index(): return send_from_directory('.', 'index.html')
 
@app.route('/uploads/<filename>')
def uploaded_file(filename): return send_from_directory(UPLOAD_DIR, filename)
 
# ── upload ────────────────────────────────────────────────────────────────
@app.route('/api/upload', methods=['POST'])
def upload():
    err = admin_required()
    if err: return err
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    f = request.files['file']
    if not f.filename or not allowed(f.filename):
        return jsonify({'error': 'Formato inválido. Use PNG, JPG, GIF ou WEBP'}), 400
    f.seek(0, 2); size_mb = f.tell() / (1024*1024); f.seek(0)
    if size_mb > MAX_MB:
        return jsonify({'error': f'Arquivo muito grande (máx {MAX_MB}MB)'}), 400
    ext      = f.filename.rsplit('.', 1)[1].lower()
    filename = f'{uuid.uuid4().hex}.{ext}'
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    f.save(os.path.join(UPLOAD_DIR, filename))
    return jsonify({'url': f'/uploads/{filename}'}), 201
 
# ── auth ──────────────────────────────────────────────────────────────────
@app.route('/api/login', methods=['POST'])
def login():
    d = request.get_json()
    if d.get('username') == ADMIN_USER and d.get('password') == ADMIN_PASS:
        session['admin'] = True
        return jsonify({'success': True})
    return jsonify({'success': False}), 401
 
@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('admin', None); return jsonify({'success': True})
 
@app.route('/api/me')
def me(): return jsonify({'admin': session.get('admin', False)})
 
# ── NEWS CRUD ─────────────────────────────────────────────────────────────
@app.route('/api/news', methods=['GET'])
def get_news(): return jsonify(load(NEWS_FILE))
 
@app.route('/api/news', methods=['POST'])
def create_news():
    err = admin_required()
    if err: return err
    d    = request.get_json()
    item = {'id': str(uuid.uuid4()), 'title': d.get('title',''), 'category': d.get('category',''),
            'content': d.get('content',''), 'icon': d.get('icon','🎶'), 'image': d.get('image',''),
            'status': d.get('status','published'), 'date': datetime.now().strftime('%d/%m/%Y')}
    news = load(NEWS_FILE); news.insert(0, item); save(NEWS_FILE, news)
    return jsonify(item), 201
 
@app.route('/api/news/<nid>', methods=['PUT'])
def update_news(nid):
    err = admin_required()
    if err: return err
    d = request.get_json(); news = load(NEWS_FILE)
    for item in news:
        if item['id'] == nid:
            item.update({k: v for k, v in d.items() if k != 'id'})
            save(NEWS_FILE, news); return jsonify(item)
    return jsonify({'error': 'Não encontrado'}), 404
 
@app.route('/api/news/<nid>', methods=['DELETE'])
def delete_news(nid):
    err = admin_required()
    if err: return err
    save(NEWS_FILE, [n for n in load(NEWS_FILE) if n['id'] != nid])
    return jsonify({'success': True})
 
# ── DJS CRUD ──────────────────────────────────────────────────────────────
@app.route('/api/djs', methods=['GET'])
def get_djs(): return jsonify(load(DJS_FILE))
 
@app.route('/api/djs', methods=['POST'])
def create_dj():
    err = admin_required()
    if err: return err
    d   = request.get_json()
    raw = d.get('decades', [])
    if isinstance(raw, str): raw = [x.strip() for x in raw.split(',') if x.strip()]
    item = {'id': str(uuid.uuid4()), 'name': d.get('name',''), 'style': d.get('style',''),
            'description': d.get('description',''), 'decades': raw,
            'color': d.get('color','linear-gradient(135deg,#ff2d78,#c400ff)'),
            'initials': d.get('initials','DJ'), 'schedule': d.get('schedule','')}
    djs = load(DJS_FILE); djs.append(item); save(DJS_FILE, djs)
    return jsonify(item), 201
 
@app.route('/api/djs/<did>', methods=['PUT'])
def update_dj(did):
    err = admin_required()
    if err: return err
    d   = request.get_json()
    raw = d.get('decades', [])
    if isinstance(raw, str): raw = [x.strip() for x in raw.split(',') if x.strip()]
    djs = load(DJS_FILE)
    for item in djs:
        if item['id'] == did:
            item.update({k: v for k, v in d.items() if k != 'id'})
            item['decades'] = raw; save(DJS_FILE, djs); return jsonify(item)
    return jsonify({'error': 'Não encontrado'}), 404
 
@app.route('/api/djs/<did>', methods=['DELETE'])
def delete_dj(did):
    err = admin_required()
    if err: return err
    save(DJS_FILE, [x for x in load(DJS_FILE) if x['id'] != did])
    return jsonify({'success': True})
 
# ── seed ──────────────────────────────────────────────────────────────────
def seed():
    os.makedirs(DATA_DIR, exist_ok=True); os.makedirs(UPLOAD_DIR, exist_ok=True)
    if not os.path.exists(NEWS_FILE):
        save(NEWS_FILE, [
            {'id':str(uuid.uuid4()),'title':'Line-up completo revelado com 8 DJs','category':'Line-up','content':'A festa FLASHBACK confirma sua maior edição com DJs especializados em décadas 70, 80 e 90.','icon':'🎶','image':'','status':'published','date':'28/05/2025'},
            {'id':str(uuid.uuid4()),'title':'Pista VIP com bola de discoteca original','category':'Estrutura','content':'A área VIP contará com bola de discoteca importada dos anos 70, criando aquele efeito nostálgico inesquecível.','icon':'🪩','image':'','status':'published','date':'22/05/2025'},
            {'id':str(uuid.uuid4()),'title':'Lote promocional esgota em 48 horas','category':'Ingressos','content':'O primeiro lote foi encerrado em tempo recorde. O segundo lote está disponível a partir de R$ 60.','icon':'🎟️','image':'','status':'published','date':'18/05/2025'},
            {'id':str(uuid.uuid4()),'title':'Regulamento do dress code retrô','category':'Dress Code','content':'Venha com o visual dos anos 80! Legging, ombreiras e mullet são bem-vindos. Fantasiados ganham cortesia no bar.','icon':'👗','image':'','status':'published','date':'15/05/2025'},
            {'id':str(uuid.uuid4()),'title':'Local: Pavilhão Sul Centro de Eventos','category':'Local','content':'A festa acontece no Pavilhão Sul com capacidade para 2.000 pessoas, estacionamento próprio e acessibilidade total.','icon':'📍','image':'','status':'published','date':'10/05/2025'},
            {'id':str(uuid.uuid4()),'title':'Open bar de bebidas retrô no VIP','category':'Gastronomia','content':'Drinks temáticos: Rum Coke dos 70, Harvey Wallbanger dos 80 e Cosmopolitan dos 90.','icon':'🍹','image':'','status':'published','date':'05/05/2025'},
        ])
    if not os.path.exists(DJS_FILE):
        save(DJS_FILE, [
            {'id':str(uuid.uuid4()),'name':'DJ Tião','style':'Disco & Funk','description':'O mestre do groove! Tião coleciona vinis desde 1976 e leva o público ao delírio com hits do Soul, Funk e Disco.','decades':['70s','80s'],'color':'linear-gradient(135deg,#ff2d78,#c400ff)','initials':'TI','schedule':'21:00 – 22:30'},
            {'id':str(uuid.uuid4()),'name':'DJ Karen','style':'New Wave & Synth','description':'Rainha do sintetizador! Especialista em New Wave, Synth Pop e Italo Disco — a trilha sonora da geração cassete.','decades':['80s'],'color':'linear-gradient(135deg,#00f0ff,#0040ff)','initials':'KA','schedule':'22:30 – 00:00'},
            {'id':str(uuid.uuid4()),'name':'DJ Marquinho','style':'Eurodance & Techno','description':'Do Eurodance ao Techno, Marquinho domina os anos 90 com energia total. Ace of Base, Snap e muito mais.','decades':['90s'],'color':'linear-gradient(135deg,#ffe600,#ff6600)','initials':'MR','schedule':'00:00 – 02:00'},
            {'id':str(uuid.uuid4()),'name':'DJ Lady Rock','style':'Pop Rock & Metal','description':'Ela comanda o palco alternativo com Guns N Roses, Nirvana e Bon Jovi. Rock puro dos 80 e 90!','decades':['80s','90s'],'color':'linear-gradient(135deg,#ff2d78,#800040)','initials':'LR','schedule':'02:00 – 03:30'},
            {'id':str(uuid.uuid4()),'name':'DJ Phunk','style':'Soul & R&B','description':'Soul profundo! De Stevie Wonder e Marvin Gaye à ebulição do R&B dos anos 90.','decades':['70s','80s','90s'],'color':'linear-gradient(135deg,#c400ff,#4400aa)','initials':'PH','schedule':'19:00 – 21:00'},
            {'id':str(uuid.uuid4()),'name':'DJ Bossa','style':'MPB & Axé','description':'O representante nacional! MPB, pagode dos 90 e axé music fazem a alegria do público brasileiro.','decades':['80s','90s'],'color':'linear-gradient(135deg,#00ff88,#008844)','initials':'BS','schedule':'18:00 – 19:00'},
        ])
 
if __name__ == '__main__':
    seed()
    print('\n  🎶  FLASHBACK rodando em http://localhost:5000\n')
    app.run(debug=True, port=5000)