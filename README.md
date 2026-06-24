# 📚 Elektron Jurnal — Kollec İdarəetmə Sistemi

## Sistem xülasəsi

| Modul | Funksiyalar |
|---|---|
| **Admin** | Müəllim, tələbə, qrup, fənn, ixtisas idarəsi; audit log |
| **Müəllim** | Davamiyyət, qiymətləndirmə, hesabat, öz profili |
| **Tələbə** | Öz kabinetini görür, şifrə dəyişir |

## Rollar və giriş

| Rol | Demo giriş | Şifrə |
|---|---|---|
| Admin | `admin` | `admin123` |
| Müəllim | `Muellim1` | `1234` |
| Tələbə | `eliyev.murad` | `1234` |

Giriş səhifəsində **Müəllim/Admin** və ya **Tələbə** tabını seçin.

---

## 🚀 Railway-ə Deploy (5 addım)

### 1. GitHub-a yükləyin
1. [github.com](https://github.com) → "New repository" → `elektron-jurnal`
2. "uploading an existing file" → ZIP içindəki bütün faylları sürükləyin
3. "Commit changes"

### 2. Railway-ə qoşun
1. [railway.app](https://railway.app) → GitHub ilə daxil olun
2. **"New Project"** → **"Deploy from GitHub repo"** → reponu seçin

### 3. PostgreSQL əlavə edin
1. Proyekt içərisində **"+ New"** → **"Database"** → **"PostgreSQL"**
2. App servisinə klikləyin → **"Variables"** tabı
3. **+ New Variable:**
   - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`
   - `SECRET_KEY` = `kollec-jurnal-sizin-gizli-sozunuz`

### 4. Domain alın
**Settings** → **Networking** → **"Generate Domain"**
→ `xxxxx.railway.app` — bütün müəllimlərə göndərin!

### 5. İlk girişdən sonra
- Admin şifrəsini dərhal dəyişin
- Admin → İxtisaslar əlavə edin
- Admin → Qruplar əlavə edin
- Admin → Müəllimlər əlavə edin
- Admin → Fənlər əlavə edin (müəllimə birləşdirin)
- Admin → Tələbələr əlavə edin (istifadəçi adı + şifrə)

---

## Funksiyalar (tam siyahı)

### ✅ Mövcud funksiyalar
- **Aktiv/Passiv** — müəllim, qrup, fənn, tələbə üçün toggle
- **Audit log** — hər əməliyyat qeyd edilir (kim, nə vaxt, nə etdi)
- **Tələbə modulu** — ad/soyad, ata adı, FİN, doğum tarixi, telefon, email, qrup, ixtisas, kurs, forma, qəbul ili, status
- **Müəllim kartı** — ad soyad, telefon, email, şöbə, fənlər, statistika
- **Davamiyyət** — tarix+fənn+qrup seçimi, İ / Q·B, avtomatik saxlama
- **Qiymətləndirmə** — Şifahi, Yazılı, Praktiki, Laboratoriya, Sərbəst iş, orta hesablama, növə görə filtr
- **Hesabat** — davamiyyət %, orta bal, Normal/Diqqət statusu, çap
- **Admin baxışı** — istənilən fənn+qrup üçün jurnal/qiymət/hesabat
- **Tələbə kabineti** — öz fənlərini, davamiyyətini, qiymətlərini görür
- **Şifrə dəyişmə** — müəllim və tələbə öz şifrəsini dəyişə bilir
- **Admin şifrə sıfırlama** — müəllim və tələbə şifrəsini admin sıfırlayır
- **Tələbə status** — aktiv / məzun / xaric edilmiş

### 📋 Texniki
- **Backend:** Python 3 + Flask + SQLAlchemy
- **DB:** PostgreSQL (Railway) / SQLite (lokal)
- **Deploy:** Railway.app (pulsuz plan)
