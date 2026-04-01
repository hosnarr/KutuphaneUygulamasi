import sqlite3

def vt_hazirla(self):
        baglanti = sqlite3.connect("kutuphane.db")
        cursor = baglanti.cursor()
        # Eğer tablo varsa bile 'barkod_no' sütununu eklemeyi dene
        try:
            cursor.execute("ALTER TABLE kitaplar ADD COLUMN barkod_no TEXT")
        except sqlite3.OperationalError:
            # Sütun zaten varsa hata vermesini engelle
            pass
            
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kitaplar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                isim TEXT NOT NULL,
                yazar TEXT NOT NULL,
                barkod_no TEXT,
                durum TEXT DEFAULT 'Mevcut'
            )
        """)
        baglanti.commit()
        baglanti.close()