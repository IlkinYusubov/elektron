import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, g
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'jurnal-secret-2024-xyz')

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///jurnal.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ══════════════════════════════════════════════════════════
#  MODELLƏR
# ══════════════════════════════════════════════════════════

class Muellim(db.Model):
    __tablename__ = 'muellim'
    id        = db.Column(db.Integer, primary_key=True)
    ad        = db.Column(db.String(100), nullable=False, unique=True)
    ad_soyad  = db.Column(db.String(150))
    sifre     = db.Column(db.String(100), nullable=False)
    rol       = db.Column(db.String(20), default='muellim')
    telefon   = db.Column(db.String(30))
    email     = db.Column(db.String(150))
    sobe      = db.Column(db.String(100))
    aktiv     = db.Column(db.Boolean, default=True)
    yaradildi = db.Column(db.DateTime, default=datetime.utcnow)

class Ixtisas(db.Model):
    __tablename__ = 'ixtisas'
    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(150), nullable=False)

class Qrup(db.Model):
    __tablename__ = 'qrup'
    id           = db.Column(db.Integer, primary_key=True)
    ad           = db.Column(db.String(50), nullable=False)
    ixtisas_id   = db.Column(db.Integer, db.ForeignKey('ixtisas.id'))
    kurs         = db.Column(db.Integer, default=1)
    tehsil_formu = db.Column(db.String(30), default='əyani')
    qebul_ili    = db.Column(db.Integer)
    aktiv        = db.Column(db.Boolean, default=True)

class Telebe(db.Model):
    __tablename__ = 'telebe'
    id              = db.Column(db.Integer, primary_key=True)
    ad_soyad        = db.Column(db.String(100), nullable=False)
    ata_adi         = db.Column(db.String(60))
    fin_kod         = db.Column(db.String(10))
    dogum_tarixi    = db.Column(db.Date)
    telefon         = db.Column(db.String(30))
    email           = db.Column(db.String(150))
    qrup_id         = db.Column(db.Integer, db.ForeignKey('qrup.id'))
    status          = db.Column(db.String(20), default='aktiv')  # aktiv, mezun, xaric
    istifadeci_adi  = db.Column(db.String(100), unique=True)
    sifre           = db.Column(db.String(100), default='1234')
    aktiv           = db.Column(db.Boolean, default=True)
    yaradildi       = db.Column(db.DateTime, default=datetime.utcnow)

class Ders(db.Model):
    __tablename__ = 'ders'
    id         = db.Column(db.Integer, primary_key=True)
    ad         = db.Column(db.String(100), nullable=False)
    muellim_id = db.Column(db.Integer, db.ForeignKey('muellim.id'))
    aktiv      = db.Column(db.Boolean, default=True)

class DersGunu(db.Model):
    __tablename__ = 'ders_gunu'
    id      = db.Column(db.Integer, primary_key=True)
    ders_id = db.Column(db.Integer, db.ForeignKey('ders.id'))
    qrup_id = db.Column(db.Integer, db.ForeignKey('qrup.id'))
    tarix   = db.Column(db.Date, nullable=False)

class Davamiyyet(db.Model):
    __tablename__ = 'davamiyyet'
    id           = db.Column(db.Integer, primary_key=True)
    telebe_id    = db.Column(db.Integer, db.ForeignKey('telebe.id'))
    ders_gunu_id = db.Column(db.Integer, db.ForeignKey('ders_gunu.id'))
    status       = db.Column(db.String(2), default='i')
    __table_args__ = (db.UniqueConstraint('telebe_id', 'ders_gunu_id'),)

class Qiymet(db.Model):
    __tablename__ = 'qiymet'
    id        = db.Column(db.Integer, primary_key=True)
    telebe_id = db.Column(db.Integer, db.ForeignKey('telebe.id'))
    ders_id   = db.Column(db.Integer, db.ForeignKey('ders.id'))
    nov       = db.Column(db.String(50))   # sifahi, yazili, praktiki, lab, serbest
    ad        = db.Column(db.String(100))
    bal       = db.Column(db.Float)
    tarix     = db.Column(db.Date, default=date.today)
    __table_args__ = (db.UniqueConstraint('telebe_id', 'ders_id', 'nov', 'ad'),)

class AuditLog(db.Model):
    __tablename__ = 'audit_log'
    id         = db.Column(db.Integer, primary_key=True)
    zaman      = db.Column(db.DateTime, default=datetime.utcnow)
    istifadeci = db.Column(db.String(120))
    rol        = db.Column(db.String(20))
    emeliyyat  = db.Column(db.String(50))
    model      = db.Column(db.String(50))
    aciklama   = db.Column(db.String(500))
    ip         = db.Column(db.String(45))

# ══════════════════════════════════════════════════════════
#  AUDIT HELPER
# ══════════════════════════════════════════════════════════

def log(emeliyyat, model, aciklama):
    try:
        istifadeci = session.get('muellim_ad') or session.get('telebe_ad') or '?'
        rol        = session.get('rol', '?')
        ip         = request.remote_addr
        db.session.add(AuditLog(
            istifadeci=istifadeci, rol=rol,
            emeliyyat=emeliyyat, model=model,
            aciklama=aciklama, ip=ip))
        db.session.flush()
    except Exception:
        pass

# ══════════════════════════════════════════════════════════
#  DEKORATORLAR
# ══════════════════════════════════════════════════════════

def giris_teleb(f):
    @wraps(f)
    def dec(*a, **kw):
        if 'muellim_id' not in session and 'telebe_id' not in session:
            return redirect(url_for('giris'))
        return f(*a, **kw)
    return dec

def muellim_teleb(f):
    @wraps(f)
    def dec(*a, **kw):
        if 'muellim_id' not in session:
            return redirect(url_for('giris'))
        m = Muellim.query.get(session['muellim_id'])
        if not m or not m.aktiv:
            session.clear()
            return redirect(url_for('giris'))
        return f(*a, **kw)
    return dec

def admin_teleb(f):
    @wraps(f)
    def dec(*a, **kw):
        if session.get('rol') != 'admin':
            return redirect(url_for('panel'))
        return f(*a, **kw)
    return dec

def telebe_teleb(f):
    @wraps(f)
    def dec(*a, **kw):
        if 'telebe_id' not in session:
            return redirect(url_for('giris'))
        return f(*a, **kw)
    return dec

# ══════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════

@app.route('/')
def index():
    if 'telebe_id' in session:
        return redirect(url_for('telebe_kabinet'))
    if 'muellim_id' in session:
        return redirect(url_for('panel'))
    return redirect(url_for('giris'))

@app.route('/giris', methods=['GET', 'POST'])
def giris():
    xeta = None
    if request.method == 'POST':
        ad    = request.form.get('ad','').strip()
        sifre = request.form.get('sifre','').strip()
        rol   = request.form.get('rol','muellim')

        if rol == 'telebe':
            t = Telebe.query.filter_by(istifadeci_adi=ad, sifre=sifre, aktiv=True).first()
            if t:
                session.clear()
                session['telebe_id'] = t.id
                session['telebe_ad'] = t.ad_soyad
                session['rol']       = 'telebe'
                log('GİRİŞ','Telebe', f'{t.ad_soyad} daxil oldu')
                db.session.commit()
                return redirect(url_for('telebe_kabinet'))
            xeta = 'İstifadəçi adı və ya şifrə səhvdir.'
        else:
            m = Muellim.query.filter_by(ad=ad, sifre=sifre, aktiv=True).first()
            if m:
                session.clear()
                session['muellim_id'] = m.id
                session['muellim_ad'] = m.ad
                session['rol']        = m.rol
                log('GİRİŞ','Muellim', f'{m.ad} daxil oldu')
                db.session.commit()
                return redirect(url_for('panel'))
            xeta = 'Ad və ya şifrə səhvdir (və ya hesab passivdir).'

    return render_template('giris.html', xeta=xeta)

@app.route('/cixis')
def cixis():
    ad = session.get('muellim_ad') or session.get('telebe_ad','')
    log('ÇIXIŞ','Auth', f'{ad} çıxdı')
    try: db.session.commit()
    except: pass
    session.clear()
    return redirect(url_for('giris'))

# ══════════════════════════════════════════════════════════
#  MÜƏLLİM PANELİ
# ══════════════════════════════════════════════════════════

@app.route('/panel')
@muellim_teleb
def panel():
    mid     = session['muellim_id']
    dersler = Ders.query.filter_by(muellim_id=mid, aktiv=True).all()
    qruplar = Qrup.query.filter_by(aktiv=True).all()
    return render_template('panel.html', dersler=dersler, qruplar=qruplar)

# ── Davamiyyət ────────────────────────────────────────────

@app.route('/jurnal')
@muellim_teleb
def jurnal():
    mid      = session['muellim_id']
    ders_id  = request.args.get('ders_id', type=int)
    qrup_id  = request.args.get('qrup_id', type=int)
    tarix_s  = request.args.get('tarix', '')
    dersler  = Ders.query.filter_by(muellim_id=mid, aktiv=True).all()
    qruplar  = Qrup.query.filter_by(aktiv=True).all()
    telebe_list, gun_list, dav_map = [], [], {}

    if ders_id and qrup_id:
        telebe_list = Telebe.query.filter_by(qrup_id=qrup_id, aktiv=True).order_by(Telebe.ad_soyad).all()
        q_gun = DersGunu.query.filter_by(ders_id=ders_id, qrup_id=qrup_id)
        if tarix_s:
            try:
                tarix_f = datetime.strptime(tarix_s, '%Y-%m-%d').date()
                q_gun = q_gun.filter_by(tarix=tarix_f)
            except: pass
        gun_list = q_gun.order_by(DersGunu.tarix).all()
        for g in gun_list:
            for dav in Davamiyyet.query.filter_by(ders_gunu_id=g.id).all():
                dav_map[(dav.telebe_id, g.id)] = dav.status

    return render_template('jurnal.html',
        dersler=dersler, qruplar=qruplar,
        ders_id=ders_id, qrup_id=qrup_id, tarix_s=tarix_s,
        telebe_list=telebe_list, gun_list=gun_list, dav_map=dav_map)

# ── Qiymətləndirmə ────────────────────────────────────────

@app.route('/qiymet')
@muellim_teleb
def qiymet_sehife():
    mid     = session['muellim_id']
    ders_id = request.args.get('ders_id', type=int)
    qrup_id = request.args.get('qrup_id', type=int)
    dersler = Ders.query.filter_by(muellim_id=mid, aktiv=True).all()
    qruplar = Qrup.query.filter_by(aktiv=True).all()
    telebe_list, qiymet_map, novler = [], {}, []

    if ders_id and qrup_id:
        telebe_list = Telebe.query.filter_by(qrup_id=qrup_id, aktiv=True).order_by(Telebe.ad_soyad).all()
        tid_list    = [t.id for t in telebe_list]
        qls         = Qiymet.query.filter(Qiymet.ders_id==ders_id, Qiymet.telebe_id.in_(tid_list)).all()
        novler      = sorted({(q.nov, q.ad) for q in qls})
        for q in qls:
            qiymet_map[(q.telebe_id, q.nov, q.ad)] = q.bal

    return render_template('qiymet.html',
        dersler=dersler, qruplar=qruplar,
        ders_id=ders_id, qrup_id=qrup_id,
        telebe_list=telebe_list, novler=novler, qiymet_map=qiymet_map)

# ── Hesabat ───────────────────────────────────────────────

@app.route('/hesabat')
@muellim_teleb
def hesabat():
    mid     = session['muellim_id']
    ders_id = request.args.get('ders_id', type=int)
    qrup_id = request.args.get('qrup_id', type=int)
    dersler = Ders.query.filter_by(muellim_id=mid, aktiv=True).all()
    qruplar = Qrup.query.filter_by(aktiv=True).all()
    rows    = []

    if ders_id and qrup_id:
        telebelr = Telebe.query.filter_by(qrup_id=qrup_id, aktiv=True).order_by(Telebe.ad_soyad).all()
        gun_say  = DersGunu.query.filter_by(ders_id=ders_id, qrup_id=qrup_id).count()
        for t in telebelr:
            istirak = Davamiyyet.query.join(DersGunu).filter(
                DersGunu.ders_id==ders_id, DersGunu.qrup_id==qrup_id,
                Davamiyyet.telebe_id==t.id, Davamiyyet.status=='i').count()
            qayib = gun_say - istirak
            fais  = round(istirak/gun_say*100) if gun_say else 0
            qls   = [q for q in Qiymet.query.filter_by(telebe_id=t.id, ders_id=ders_id).all() if q.bal is not None]
            orta  = round(sum(q.bal for q in qls)/len(qls)) if qls else None
            ok    = fais >= 70 and (orta is None or orta >= 51)
            rows.append(dict(telebe=t.ad_soyad, istirak=istirak,
                             qayib=qayib, fais=fais, orta=orta,
                             status='normal' if ok else 'diqqet'))

    return render_template('hesabat.html',
        dersler=dersler, qruplar=qruplar,
        ders_id=ders_id, qrup_id=qrup_id, rows=rows)

# ══════════════════════════════════════════════════════════
#  ADMIN
# ══════════════════════════════════════════════════════════

@app.route('/admin')
@muellim_teleb
@admin_teleb
def admin():
    muellimler = Muellim.query.order_by(Muellim.ad).all()
    dersler    = Ders.query.all()
    qruplar    = Qrup.query.order_by(Qrup.ad).all()
    telebelr   = Telebe.query.order_by(Telebe.qrup_id, Telebe.ad_soyad).all()
    ixtisaslar = Ixtisas.query.all()
    return render_template('admin.html',
        muellimler=muellimler, dersler=dersler,
        qruplar=qruplar, telebelr=telebelr, ixtisaslar=ixtisaslar)

@app.route('/admin/jurnal')
@muellim_teleb
@admin_teleb
def admin_jurnal():
    ders_id = request.args.get('ders_id', type=int)
    qrup_id = request.args.get('qrup_id', type=int)
    dersler = Ders.query.filter_by(aktiv=True).all()
    qruplar = Qrup.query.filter_by(aktiv=True).all()
    telebe_list, gun_list, dav_map = [], [], {}
    ders_adi, qrup_adi = '', ''
    if ders_id and qrup_id:
        d = Ders.query.get(ders_id); q = Qrup.query.get(qrup_id)
        ders_adi = d.ad if d else ''; qrup_adi = q.ad if q else ''
        telebe_list = Telebe.query.filter_by(qrup_id=qrup_id, aktiv=True).order_by(Telebe.ad_soyad).all()
        gun_list    = DersGunu.query.filter_by(ders_id=ders_id, qrup_id=qrup_id).order_by(DersGunu.tarix).all()
        for g in gun_list:
            for dav in Davamiyyet.query.filter_by(ders_gunu_id=g.id).all():
                dav_map[(dav.telebe_id, g.id)] = dav.status
    return render_template('admin_jurnal.html',
        dersler=dersler, qruplar=qruplar, ders_id=ders_id, qrup_id=qrup_id,
        ders_adi=ders_adi, qrup_adi=qrup_adi,
        telebe_list=telebe_list, gun_list=gun_list, dav_map=dav_map)

@app.route('/admin/qiymet')
@muellim_teleb
@admin_teleb
def admin_qiymet():
    ders_id = request.args.get('ders_id', type=int)
    qrup_id = request.args.get('qrup_id', type=int)
    dersler = Ders.query.filter_by(aktiv=True).all()
    qruplar = Qrup.query.filter_by(aktiv=True).all()
    telebe_list, qiymet_map, novler = [], {}, []
    ders_adi, qrup_adi = '', ''
    if ders_id and qrup_id:
        d = Ders.query.get(ders_id); q = Qrup.query.get(qrup_id)
        ders_adi = d.ad if d else ''; qrup_adi = q.ad if q else ''
        telebe_list = Telebe.query.filter_by(qrup_id=qrup_id, aktiv=True).order_by(Telebe.ad_soyad).all()
        tid_list    = [t.id for t in telebe_list]
        qls         = Qiymet.query.filter(Qiymet.ders_id==ders_id, Qiymet.telebe_id.in_(tid_list)).all()
        novler      = sorted({(q2.nov, q2.ad) for q2 in qls})
        for q2 in qls:
            qiymet_map[(q2.telebe_id, q2.nov, q2.ad)] = q2.bal
    return render_template('admin_qiymet.html',
        dersler=dersler, qruplar=qruplar, ders_id=ders_id, qrup_id=qrup_id,
        ders_adi=ders_adi, qrup_adi=qrup_adi,
        telebe_list=telebe_list, novler=novler, qiymet_map=qiymet_map)

@app.route('/admin/hesabat')
@muellim_teleb
@admin_teleb
def admin_hesabat():
    ders_id = request.args.get('ders_id', type=int)
    qrup_id = request.args.get('qrup_id', type=int)
    dersler = Ders.query.filter_by(aktiv=True).all()
    qruplar = Qrup.query.filter_by(aktiv=True).all()
    rows = []; ders_adi, qrup_adi = '', ''
    if ders_id and qrup_id:
        d = Ders.query.get(ders_id); q = Qrup.query.get(qrup_id)
        ders_adi = d.ad if d else ''; qrup_adi = q.ad if q else ''
        telebelr = Telebe.query.filter_by(qrup_id=qrup_id, aktiv=True).order_by(Telebe.ad_soyad).all()
        gun_say  = DersGunu.query.filter_by(ders_id=ders_id, qrup_id=qrup_id).count()
        for t in telebelr:
            istirak = Davamiyyet.query.join(DersGunu).filter(
                DersGunu.ders_id==ders_id, DersGunu.qrup_id==qrup_id,
                Davamiyyet.telebe_id==t.id, Davamiyyet.status=='i').count()
            qayib = gun_say - istirak
            fais  = round(istirak/gun_say*100) if gun_say else 0
            qls   = [q2 for q2 in Qiymet.query.filter_by(telebe_id=t.id, ders_id=ders_id).all() if q2.bal is not None]
            orta  = round(sum(q2.bal for q2 in qls)/len(qls)) if qls else None
            ok    = fais >= 70 and (orta is None or orta >= 51)
            rows.append(dict(telebe=t.ad_soyad, istirak=istirak,
                             qayib=qayib, fais=fais, orta=orta,
                             status='normal' if ok else 'diqqet'))
    return render_template('admin_hesabat.html',
        dersler=dersler, qruplar=qruplar, ders_id=ders_id, qrup_id=qrup_id,
        ders_adi=ders_adi, qrup_adi=qrup_adi, rows=rows)

@app.route('/admin/audit')
@muellim_teleb
@admin_teleb
def admin_audit():
    sehife   = request.args.get('s', 1, type=int)
    istifadeci_f = request.args.get('istifadeci', '').strip()
    emeliyyat_f  = request.args.get('emeliyyat', '').strip()
    q = AuditLog.query.order_by(AuditLog.zaman.desc())
    if istifadeci_f: q = q.filter(AuditLog.istifadeci.ilike(f'%{istifadeci_f}%'))
    if emeliyyat_f:  q = q.filter(AuditLog.emeliyyat==emeliyyat_f)
    logs = q.paginate(page=sehife, per_page=50, error_out=False)
    emeller = db.session.query(AuditLog.emeliyyat).distinct().all()
    emeller = [e[0] for e in emeller]
    return render_template('admin_audit.html', logs=logs,
        istifadeci_f=istifadeci_f, emeliyyat_f=emeliyyat_f, emeller=emeller)

@app.route('/admin/muellim/<int:mid>')
@muellim_teleb
@admin_teleb
def admin_muellim_kart(mid):
    m = Muellim.query.get_or_404(mid)
    dersler = Ders.query.filter_by(muellim_id=mid).all()
    ders_ids = [d.id for d in dersler]
    kecilen = DersGunu.query.filter(DersGunu.ders_id.in_(ders_ids)).count() if ders_ids else 0
    return render_template('admin_muellim_kart.html', m=m, dersler=dersler, kecilen=kecilen)

@app.route('/admin/telebe/<int:tid>')
@muellim_teleb
@admin_teleb
def admin_telebe_kart(tid):
    t    = Telebe.query.get_or_404(tid)
    qrup = Qrup.query.get(t.qrup_id)
    ixt  = Ixtisas.query.get(qrup.ixtisas_id) if qrup and qrup.ixtisas_id else None
    # Dərs statistikası
    ders_ids = db.session.query(DersGunu.ders_id).filter_by(qrup_id=t.qrup_id).distinct()
    dersler_stat = []
    for did in ders_ids:
        d = Ders.query.get(did[0])
        if not d: continue
        gun_say = DersGunu.query.filter_by(ders_id=d.id, qrup_id=t.qrup_id).count()
        istirak = Davamiyyet.query.join(DersGunu).filter(
            DersGunu.ders_id==d.id, DersGunu.qrup_id==t.qrup_id,
            Davamiyyet.telebe_id==t.id, Davamiyyet.status=='i').count()
        fais = round(istirak/gun_say*100) if gun_say else 0
        qls  = [q for q in Qiymet.query.filter_by(telebe_id=t.id, ders_id=d.id).all() if q.bal is not None]
        orta = round(sum(q.bal for q in qls)/len(qls)) if qls else None
        dersler_stat.append(dict(ad=d.ad, gun_say=gun_say, istirak=istirak,
                                  qayib=gun_say-istirak, fais=fais, orta=orta))
    return render_template('admin_telebe_kart.html', t=t, qrup=qrup, ixt=ixt, dersler_stat=dersler_stat)

# ══════════════════════════════════════════════════════════
#  TƏLƏBƏ KABİNETİ
# ══════════════════════════════════════════════════════════

@app.route('/kabinet')
@telebe_teleb
def telebe_kabinet():
    tid    = session['telebe_id']
    telebe = Telebe.query.get(tid)
    qrup   = Qrup.query.get(telebe.qrup_id)
    ixt    = Ixtisas.query.get(qrup.ixtisas_id) if qrup and qrup.ixtisas_id else None
    gun_ders_ids = db.session.query(DersGunu.ders_id).filter_by(qrup_id=telebe.qrup_id).distinct()
    dersler = Ders.query.filter(Ders.id.in_(gun_ders_ids), Ders.aktiv==True).all()
    ders_melumat = []
    for d in dersler:
        muellim  = Muellim.query.get(d.muellim_id)
        gun_say  = DersGunu.query.filter_by(ders_id=d.id, qrup_id=telebe.qrup_id).count()
        istirak  = Davamiyyet.query.join(DersGunu).filter(
                    DersGunu.ders_id==d.id, DersGunu.qrup_id==telebe.qrup_id,
                    Davamiyyet.telebe_id==tid, Davamiyyet.status=='i').count()
        fais     = round(istirak/gun_say*100) if gun_say else 0
        qls      = [q for q in Qiymet.query.filter_by(telebe_id=tid, ders_id=d.id).all() if q.bal is not None]
        orta     = round(sum(q.bal for q in qls)/len(qls)) if qls else None
        ders_melumat.append(dict(
            id=d.id, ad=d.ad, muellim=muellim.ad_soyad or muellim.ad if muellim else '—',
            gun_say=gun_say, istirak=istirak, qayib=gun_say-istirak, fais=fais, orta=orta,
            status='normal' if fais>=70 and (orta is None or orta>=51) else 'diqqet'))
    return render_template('telebe_kabinet.html',
        telebe=telebe, qrup=qrup, ixt=ixt, dersler=ders_melumat)

@app.route('/kabinet/ders/<int:ders_id>')
@telebe_teleb
def telebe_ders(ders_id):
    tid     = session['telebe_id']
    telebe  = Telebe.query.get(tid)
    ders    = Ders.query.get_or_404(ders_id)
    qrup    = Qrup.query.get(telebe.qrup_id)
    muellim = Muellim.query.get(ders.muellim_id)
    gun_list = DersGunu.query.filter_by(ders_id=ders_id, qrup_id=telebe.qrup_id).order_by(DersGunu.tarix).all()
    dav_list = []
    istirak_say = 0
    for g in gun_list:
        dav = Davamiyyet.query.filter_by(telebe_id=tid, ders_gunu_id=g.id).first()
        st  = dav.status if dav else 'i'
        if st == 'i': istirak_say += 1
        dav_list.append({'tarix': g.tarix, 'status': st})
    gun_say = len(gun_list)
    fais    = round(istirak_say/gun_say*100) if gun_say else 0
    qls     = Qiymet.query.filter_by(telebe_id=tid, ders_id=ders_id).order_by(Qiymet.tarix).all()
    orta    = round(sum(q.bal for q in qls if q.bal is not None)/
                    len([q for q in qls if q.bal is not None])) if any(q.bal is not None for q in qls) else None
    return render_template('telebe_ders.html',
        telebe=telebe, ders=ders, qrup=qrup, muellim=muellim,
        dav_list=dav_list, gun_say=gun_say, istirak_say=istirak_say, fais=fais,
        qls=qls, orta=orta)

@app.route('/kabinet/profil', methods=['GET','POST'])
@telebe_teleb
def telebe_profil():
    tid    = session['telebe_id']
    telebe = Telebe.query.get(tid)
    xeta   = None; ugur = None
    if request.method == 'POST':
        tur = request.form.get('tur')
        if tur == 'sifre':
            kohne = request.form.get('kohne_sifre','').strip()
            yeni  = request.form.get('yeni_sifre','').strip()
            yeni2 = request.form.get('yeni_sifre2','').strip()
            if kohne != telebe.sifre:
                xeta = 'Köhnə şifrə səhvdir.'
            elif len(yeni) < 4:
                xeta = 'Yeni şifrə ən az 4 simvol olmalıdır.'
            elif yeni != yeni2:
                xeta = 'Yeni şifrələr uyğun gəlmir.'
            else:
                telebe.sifre = yeni
                log('ŞIFRƏ','Telebe', f'{telebe.ad_soyad} şifrəsini dəyişdi')
                db.session.commit()
                ugur = 'Şifrə uğurla dəyişdirildi!'
        elif tur == 'meluat':
            telebe.email   = request.form.get('email','').strip()
            telebe.telefon = request.form.get('telefon','').strip()
            log('YENİLƏ','Telebe', f'{telebe.ad_soyad} profilini yenilədi')
            db.session.commit()
            ugur = 'Məlumatlar yeniləndi!'
    return render_template('telebe_profil.html', telebe=telebe, xeta=xeta, ugur=ugur)

# ══════════════════════════════════════════════════════════
#  API — DAVAMIYYƏT
# ══════════════════════════════════════════════════════════

@app.route('/api/davamiyyet', methods=['POST'])
@muellim_teleb
def api_davamiyyet():
    d   = request.json
    rec = Davamiyyet.query.filter_by(telebe_id=d['telebe_id'], ders_gunu_id=d['ders_gunu_id']).first()
    t   = Telebe.query.get(d['telebe_id'])
    if rec:
        rec.status = d['status']
    else:
        rec = Davamiyyet(telebe_id=d['telebe_id'], ders_gunu_id=d['ders_gunu_id'], status=d['status'])
        db.session.add(rec)
    log('DAVAMİYYƏT','Davamiyyet', f"{t.ad_soyad if t else '?'} → {d['status']}")
    db.session.commit()
    return jsonify(ok=True)

@app.route('/api/gun_elave', methods=['POST'])
@muellim_teleb
def api_gun_elave():
    d     = request.json
    tarix = datetime.strptime(d['tarix'], '%Y-%m-%d').date()
    if DersGunu.query.filter_by(ders_id=d['ders_id'], qrup_id=d['qrup_id'], tarix=tarix).first():
        return jsonify(ok=False, xeta='Bu tarix artıq mövcuddur.')
    gun = DersGunu(ders_id=d['ders_id'], qrup_id=d['qrup_id'], tarix=tarix)
    db.session.add(gun)
    db.session.flush()
    for t in Telebe.query.filter_by(qrup_id=d['qrup_id'], aktiv=True).all():
        db.session.add(Davamiyyet(telebe_id=t.id, ders_gunu_id=gun.id, status='i'))
    der = Ders.query.get(d['ders_id'])
    qrp = Qrup.query.get(d['qrup_id'])
    log('ƏLAVƏ','DersGunu', f"{der.ad if der else '?'} — {qrp.ad if qrp else '?'} — {tarix}")
    db.session.commit()
    return jsonify(ok=True, gun_id=gun.id, tarix_str=tarix.strftime('%d.%m'))

@app.route('/api/gun_sil', methods=['POST'])
@muellim_teleb
def api_gun_sil():
    gid = request.json['gun_id']
    g   = DersGunu.query.get(gid)
    log('SİL','DersGunu', f"Gun {gid} silindi — {g.tarix if g else ''}")
    Davamiyyet.query.filter_by(ders_gunu_id=gid).delete()
    DersGunu.query.filter_by(id=gid).delete()
    db.session.commit()
    return jsonify(ok=True)

# ══════════════════════════════════════════════════════════
#  API — QİYMƏT
# ══════════════════════════════════════════════════════════

@app.route('/api/qiymet', methods=['POST'])
@muellim_teleb
def api_qiymet():
    d   = request.json
    rec = Qiymet.query.filter_by(telebe_id=d['telebe_id'], ders_id=d['ders_id'],
                                   nov=d['nov'], ad=d['ad']).first()
    t   = Telebe.query.get(d['telebe_id'])
    if d['bal'] is None or d['bal'] == '':
        if rec: db.session.delete(rec)
    else:
        bal = float(d['bal'])
        if rec: rec.bal = bal
        else:
            db.session.add(Qiymet(telebe_id=d['telebe_id'], ders_id=d['ders_id'],
                                   nov=d['nov'], ad=d['ad'], bal=bal))
    log('QİYMƏT','Qiymet', f"{t.ad_soyad if t else '?'} — {d['nov']} {d['ad']} → {d['bal']}")
    db.session.commit()
    return jsonify(ok=True)

@app.route('/api/qiymet_sutun', methods=['POST'])
@muellim_teleb
def api_qiymet_sutun():
    d        = request.json
    telebelr = Telebe.query.filter_by(qrup_id=d['qrup_id'], aktiv=True).all()
    for t in telebelr:
        if not Qiymet.query.filter_by(telebe_id=t.id, ders_id=d['ders_id'],
                                       nov=d['nov'], ad=d['ad']).first():
            db.session.add(Qiymet(telebe_id=t.id, ders_id=d['ders_id'],
                                   nov=d['nov'], ad=d['ad'], bal=None))
    log('SUTUN','Qiymet', f"Yeni sütun: {d['nov']} — {d['ad']}")
    db.session.commit()
    return jsonify(ok=True)

# ══════════════════════════════════════════════════════════
#  API — ADMIN
# ══════════════════════════════════════════════════════════

@app.route('/api/admin/muellim_elave', methods=['POST'])
@muellim_teleb
@admin_teleb
def api_muellim_elave():
    d = request.json
    if Muellim.query.filter_by(ad=d['ad']).first():
        return jsonify(ok=False, xeta='Bu istifadəçi adı artıq mövcuddur.')
    m = Muellim(ad=d['ad'], sifre=d['sifre'], rol=d.get('rol','muellim'),
                ad_soyad=d.get('ad_soyad',''), telefon=d.get('telefon',''),
                email=d.get('email',''), sobe=d.get('sobe',''))
    db.session.add(m)
    log('ƏLAVƏ','Muellim', f"Yeni müəllim: {d['ad']}")
    db.session.commit()
    return jsonify(ok=True, id=m.id)

@app.route('/api/admin/muellim_aktiv', methods=['POST'])
@muellim_teleb
@admin_teleb
def api_muellim_aktiv():
    d = request.json
    m = Muellim.query.get(d['id'])
    if not m: return jsonify(ok=False)
    m.aktiv = d['aktiv']
    log('AKTİVLİK','Muellim', f"{m.ad} → {'aktiv' if d['aktiv'] else 'passiv'}")
    db.session.commit()
    return jsonify(ok=True)

@app.route('/api/admin/muellim_sil', methods=['POST'])
@muellim_teleb
@admin_teleb
def api_muellim_sil():
    mid = request.json['id']
    m   = Muellim.query.get(mid)
    log('SİL','Muellim', f"{m.ad if m else mid} silindi")
    Ders.query.filter_by(muellim_id=mid).delete()
    Muellim.query.filter_by(id=mid).delete()
    db.session.commit()
    return jsonify(ok=True)

@app.route('/api/admin/ders_elave', methods=['POST'])
@muellim_teleb
@admin_teleb
def api_ders_elave():
    d   = request.json
    obj = Ders(ad=d['ad'], muellim_id=d['muellim_id'])
    db.session.add(obj)
    log('ƏLAVƏ','Ders', f"Yeni dərs: {d['ad']}")
    db.session.commit()
    return jsonify(ok=True, id=obj.id)

@app.route('/api/admin/ders_aktiv', methods=['POST'])
@muellim_teleb
@admin_teleb
def api_ders_aktiv():
    d   = request.json
    obj = Ders.query.get(d['id'])
    if not obj: return jsonify(ok=False)
    obj.aktiv = d['aktiv']
    log('AKTİVLİK','Ders', f"{obj.ad} → {'aktiv' if d['aktiv'] else 'passiv'}")
    db.session.commit()
    return jsonify(ok=True)

@app.route('/api/admin/ixtisas_elave', methods=['POST'])
@muellim_teleb
@admin_teleb
def api_ixtisas_elave():
    d = request.json
    i = Ixtisas(ad=d['ad'])
    db.session.add(i)
    log('ƏLAVƏ','Ixtisas', f"Yeni ixtisas: {d['ad']}")
    db.session.commit()
    return jsonify(ok=True, id=i.id)

@app.route('/api/admin/qrup_elave', methods=['POST'])
@muellim_teleb
@admin_teleb
def api_qrup_elave():
    d = request.json
    q = Qrup(ad=d['ad'], ixtisas_id=d.get('ixtisas_id'),
             kurs=d.get('kurs',1), tehsil_formu=d.get('tehsil_formu','əyani'),
             qebul_ili=d.get('qebul_ili'))
    db.session.add(q)
    log('ƏLAVƏ','Qrup', f"Yeni qrup: {d['ad']}")
    db.session.commit()
    return jsonify(ok=True, id=q.id)

@app.route('/api/admin/qrup_aktiv', methods=['POST'])
@muellim_teleb
@admin_teleb
def api_qrup_aktiv():
    d = request.json
    q = Qrup.query.get(d['id'])
    if not q: return jsonify(ok=False)
    q.aktiv = d['aktiv']
    log('AKTİVLİK','Qrup', f"{q.ad} → {'aktiv' if d['aktiv'] else 'passiv'}")
    db.session.commit()
    return jsonify(ok=True)

@app.route('/api/admin/telebe_elave', methods=['POST'])
@muellim_teleb
@admin_teleb
def api_telebe_elave():
    d = request.json
    if d.get('istifadeci_adi') and Telebe.query.filter_by(istifadeci_adi=d['istifadeci_adi']).first():
        return jsonify(ok=False, xeta='Bu istifadəçi adı artıq mövcuddur.')
    if d.get('fin_kod') and Telebe.query.filter_by(fin_kod=d['fin_kod']).first():
        return jsonify(ok=False, xeta='Bu FİN kod artıq qeydiyyatdadır.')
    t = Telebe(
        ad_soyad=d['ad_soyad'], ata_adi=d.get('ata_adi',''),
        fin_kod=d.get('fin_kod',''), qrup_id=d['qrup_id'],
        telefon=d.get('telefon',''), email=d.get('email',''),
        istifadeci_adi=d.get('istifadeci_adi') or None,
        sifre=d.get('sifre','1234'), status='aktiv'
    )
    db.session.add(t)
    log('ƏLAVƏ','Telebe', f"Yeni tələbə: {d['ad_soyad']}")
    db.session.commit()
    return jsonify(ok=True, id=t.id)

@app.route('/api/admin/telebe_aktiv', methods=['POST'])
@muellim_teleb
@admin_teleb
def api_telebe_aktiv():
    d = request.json
    t = Telebe.query.get(d['id'])
    if not t: return jsonify(ok=False)
    t.aktiv  = d['aktiv']
    t.status = d.get('status', 'aktiv' if d['aktiv'] else 'xaric')
    log('AKTİVLİK','Telebe', f"{t.ad_soyad} → {t.status}")
    db.session.commit()
    return jsonify(ok=True)

@app.route('/api/admin/telebe_sil', methods=['POST'])
@muellim_teleb
@admin_teleb
def api_telebe_sil():
    tid = request.json['id']
    t   = Telebe.query.get(tid)
    log('SİL','Telebe', f"{t.ad_soyad if t else tid} silindi")
    Davamiyyet.query.filter_by(telebe_id=tid).delete()
    Qiymet.query.filter_by(telebe_id=tid).delete()
    Telebe.query.filter_by(id=tid).delete()
    db.session.commit()
    return jsonify(ok=True)

@app.route('/api/admin/telebe_sifre_sifirla', methods=['POST'])
@muellim_teleb
@admin_teleb
def api_telebe_sifre_sifirla():
    d = request.json
    t = Telebe.query.get(d['id'])
    if not t: return jsonify(ok=False, xeta='Tələbə tapılmadı.')
    t.sifre = d.get('yeni_sifre','1234')
    log('ŞIFRƏ','Telebe', f"{t.ad_soyad} şifrəsi sıfırlandı")
    db.session.commit()
    return jsonify(ok=True)

# ══════════════════════════════════════════════════════════
#  SEED
# ══════════════════════════════════════════════════════════

def seed():
    if Muellim.query.first(): return
    adm = Muellim(ad='admin', sifre='admin123', rol='admin', ad_soyad='Sistem Admini', aktiv=True)
    m1  = Muellim(ad='Muellim1', sifre='1234', rol='muellim',
                  ad_soyad='Əliyev Əli Nəsirov', sobe='Riyaziyyat şöbəsi', aktiv=True)
    db.session.add_all([adm, m1]); db.session.flush()

    ixt1 = Ixtisas(ad='Proqram təminatı mühəndisliyi')
    ixt2 = Ixtisas(ad='İqtisadiyyat')
    db.session.add_all([ixt1, ixt2]); db.session.flush()

    q1 = Qrup(ad='101-ci qrup', ixtisas_id=ixt1.id, kurs=1, tehsil_formu='əyani', qebul_ili=2024)
    q2 = Qrup(ad='102-ci qrup', ixtisas_id=ixt2.id, kurs=1, tehsil_formu='əyani', qebul_ili=2024)
    db.session.add_all([q1, q2]); db.session.flush()

    d1 = Ders(ad='Riyaziyyat', muellim_id=m1.id)
    d2 = Ders(ad='Fizika',     muellim_id=m1.id)
    db.session.add_all([d1, d2]); db.session.flush()

    students = [
        ('Əliyev Murad','Əli','eliyev.murad','AA1234567'),
        ('Həsənova Günel','Rauf','hesenova.gunel','BB2345678'),
        ('Nəcəfov Tural','Namiq','necefov.tural','CC3456789'),
        ('Quliyeva Aytən','Fərid','quliyeva.ayten','DD4567890'),
        ('Babayev Orxan','Elnur','babayev.orxan','EE5678901'),
        ('Məmmədli Leyla','Tural','memmedli.leyla','FF6789012'),
    ]
    from datetime import date as dt
    tlist = []
    for i,(ad,ata,iad,fin) in enumerate(students):
        t = Telebe(ad_soyad=ad, ata_adi=ata, fin_kod=fin, qrup_id=q1.id,
                   istifadeci_adi=iad, sifre='1234', status='aktiv',
                   dogum_tarixi=dt(2006+i%3,1+i,10+i))
        db.session.add(t); tlist.append(t)
    db.session.flush()

    from datetime import timedelta
    import random; random.seed(42)
    base = dt(2025, 9, 2)
    for i in range(8):
        tarix = base + timedelta(weeks=i)
        for ders in [d1, d2]:
            g = DersGunu(ders_id=ders.id, qrup_id=q1.id, tarix=tarix)
            db.session.add(g); db.session.flush()
            for j,t in enumerate(tlist):
                st = 'q' if (i+j)%5==0 else 'i'
                db.session.add(Davamiyyet(telebe_id=t.id, ders_gunu_id=g.id, status=st))

    novler = [('Şifahi','Şifahi 1'),('Yazılı','Yazılı 1'),('Praktiki','Praktiki 1'),
              ('Laboratoriya','Lab 1'),('Sərbəst iş','Sərbəst 1')]
    for t in tlist:
        for ders in [d1, d2]:
            for nov,ad in novler:
                db.session.add(Qiymet(telebe_id=t.id, ders_id=ders.id,
                                       nov=nov, ad=ad, bal=random.randint(55,98)))
    db.session.commit()

with app.app_context():
    db.create_all()
    seed()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

# ══════════════════════════════════════════════════════════
#  MÜƏLLİM PROFİLİ (özü üçün)
# ══════════════════════════════════════════════════════════

@app.route('/profil', methods=['GET', 'POST'])
@muellim_teleb
def muellim_profil():
    mid    = session['muellim_id']
    m      = Muellim.query.get(mid)
    xeta   = None
    ugur   = None

    if request.method == 'POST':
        tur = request.form.get('tur')
        if tur == 'sifre':
            kohne = request.form.get('kohne', '').strip()
            yeni  = request.form.get('yeni', '').strip()
            yeni2 = request.form.get('yeni2', '').strip()
            if kohne != m.sifre:
                xeta = 'Köhnə şifrə səhvdir.'
            elif len(yeni) < 4:
                xeta = 'Yeni şifrə ən az 4 simvol olmalıdır.'
            elif yeni != yeni2:
                xeta = 'Şifrələr uyğun gəlmir.'
            else:
                m.sifre = yeni
                log('ŞIFRƏ', 'Muellim', f'{m.ad} şifrəsini dəyişdi')
                db.session.commit()
                ugur = 'Şifrə uğurla dəyişdirildi!'
        elif tur == 'meluat':
            m.ad_soyad = request.form.get('ad_soyad', '').strip()
            m.telefon  = request.form.get('telefon', '').strip()
            m.email    = request.form.get('email', '').strip()
            m.sobe     = request.form.get('sobe', '').strip()
            log('YENİLƏ', 'Muellim', f'{m.ad} profilini yenilədi')
            db.session.commit()
            ugur = 'Məlumatlar yeniləndi!'

    dersler = Ders.query.filter_by(muellim_id=mid).all()
    ders_ids = [d.id for d in dersler]
    kecilen = DersGunu.query.filter(
        DersGunu.ders_id.in_(ders_ids)).count() if ders_ids else 0

    return render_template('muellim_profil.html',
        m=m, xeta=xeta, ugur=ugur,
        dersler=dersler, kecilen=kecilen)


# ══════════════════════════════════════════════════════════
#  API — TƏLƏBƏ STATUS
# ══════════════════════════════════════════════════════════

@app.route('/api/admin/telebe_status', methods=['POST'])
@muellim_teleb
@admin_teleb
def api_telebe_status():
    d = request.json
    t = Telebe.query.get(d['id'])
    if not t:
        return jsonify(ok=False, xeta='Tapılmadı.')
    t.status = d['status']
    if d['status'] in ('mezun', 'xaric'):
        t.aktiv = False
    else:
        t.aktiv = True
    log('STATUS', 'Telebe', f'{t.ad_soyad} → {d["status"]}')
    db.session.commit()
    return jsonify(ok=True)

@app.route('/api/admin/muellim_sifre', methods=['POST'])
@muellim_teleb
@admin_teleb
def api_muellim_sifre():
    d = request.json
    m = Muellim.query.get(d['id'])
    if not m:
        return jsonify(ok=False, xeta='Tapılmadı.')
    m.sifre = d.get('sifre', '1234')
    log('ŞIFRƏ', 'Muellim', f'{m.ad} şifrəsi sıfırlandı')
    db.session.commit()
    return jsonify(ok=True)
