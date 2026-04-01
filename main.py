import sys
import sqlite3
import pandas as pd
import random
import os
import barcode
from barcode.writer import ImageWriter
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QFileDialog, QMessageBox, QDialog, QFormLayout, QInputDialog, QListWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

# --- ZİMMETLEME PENCERESİ ---
# Bu sınıf, bir kitabı belirli bir öğrenciye atamak (ödünç vermek) için açılan küçük penceredir.
class ZimmetlePenceresi(QDialog):
    def __init__(self, ogrenci_listesi, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kitap Zimmetle")
        self.setFixedWidth(450)
        self.setFixedHeight(500)
        # CSS benzeri StyleSheet ile modern bir görünüm kazandırıyoruz.
        self.setStyleSheet("background-color: #ffffff; font-family: 'Segoe UI', sans-serif;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        baslik = QLabel("Öğrenci Seçimi")
        baslik.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a2a6c;")
        layout.addWidget(baslik)

        # Arama kutusu: Liste içinde anlık filtreleme yapar.
        self.txt_ogrenci_ara = QLineEdit()
        self.txt_ogrenci_ara.setPlaceholderText("Öğrenci adı veya no ile ara...")
        self.txt_ogrenci_ara.setStyleSheet("""
            QLineEdit { border: 1px solid #ddd; border-radius: 8px; padding: 10px; background: #fcfcfc; }
            QLineEdit:focus { border: 1px solid #3498db; }
        """)
        self.txt_ogrenci_ara.textChanged.connect(self.liste_filtrele)
        layout.addWidget(self.txt_ogrenci_ara)

        # Öğrenci listesinin görüntülendiği widget.
        self.liste_widget = QListWidget()
        self.liste_widget.addItems(ogrenci_listesi)
        self.liste_widget.setStyleSheet("""
            QListWidget { border: 1px solid #eee; border-radius: 8px; padding: 5px; outline: 0; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #f9f9f9; }
            QListWidget::item:selected { background-color: #3498db; color: white; border-radius: 5px; }
        """)
        layout.addWidget(self.liste_widget)

        self.btn_onayla = QPushButton("Seçili Öğrenciye Zimmetle")
        self.btn_onayla.setStyleSheet("""
            background-color: #3498db; color: white; border-radius: 8px; 
            padding: 12px; font-weight: bold; border: none;
        """)
        self.btn_onayla.setCursor(Qt.PointingHandCursor)
        self.btn_onayla.clicked.connect(self.accept) # Pencereyi OK sonucuyla kapatır
        layout.addWidget(self.btn_onayla)

    # Yazı yazıldıkça listedeki öğrencileri gizler veya gösterir.
    def liste_filtrele(self, metin):
        for i in range(self.liste_widget.count()):
            item = self.liste_widget.item(i)
            item.setHidden(metin.lower() not in item.text().lower())

    # Seçilen öğrencinin metin bilgisini ana pencereye döndürür.
    def secilen_ogrenci(self):
        return self.liste_widget.currentItem().text() if self.liste_widget.currentItem() else None

# --- KİTAP EKLEME PENCERESİ ---
# Yeni kitapların manuel olarak sisteme girilmesini sağlar.
class KitapEklePenceresi(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni Kitap Kaydı")
        self.setFixedWidth(400)
        self.setStyleSheet("background-color: #ffffff; font-family: 'Segoe UI', sans-serif;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        baslik = QLabel("Kitap Bilgileri")
        baslik.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a2a6c; margin-bottom: 10px;")
        layout.addWidget(baslik)

        # Form düzeni: Etiket ve giriş kutularını yan yana getirir.
        self.form_layout = QFormLayout()
        self.form_layout.setSpacing(10)

        self.txt_ad = self.modern_input("Kitap Adı...")
        self.txt_yazar = self.modern_input("Yazar...")
        self.txt_kategori = self.modern_input("Kategori (Roman, Tarih vb.)...")

        self.form_layout.addRow("Kitap Adı:", self.txt_ad)
        self.form_layout.addRow("Yazar:", self.txt_yazar)
        self.form_layout.addRow("Kategori:", self.txt_kategori)
        layout.addLayout(self.form_layout)

        self.btn_kaydet = QPushButton("Sisteme Kaydet")
        self.btn_kaydet.setStyleSheet("background-color: #2ecc71; color: white; border-radius: 6px; padding: 10px; font-weight: bold; border: none;")
        self.btn_kaydet.clicked.connect(self.accept)
        layout.addWidget(self.btn_kaydet)

    # Giriş kutuları için ortak stil fonksiyonu.
    def modern_input(self, placeholder):
        txt = QLineEdit()
        txt.setPlaceholderText(placeholder)
        txt.setStyleSheet("QLineEdit { border: 1px solid #ddd; border-radius: 5px; padding: 8px; background-color: #f9f9f9; } QLineEdit:focus { border: 1px solid #1a2a6c; background-color: #fff; }")
        return txt

    def verileri_al(self):
        return self.txt_ad.text(), self.txt_yazar.text(), self.txt_kategori.text()

# --- ANA UYGULAMA SINIFI ---
class KutuphaneUygulamasi(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kütüphane Takip Sistemi")
        self.setGeometry(100, 100, 1200, 850)
        self.setStyleSheet("background-color: #ffffff; font-family: 'Segoe UI', sans-serif;")
        
        # Barkod görsellerinin kaydedileceği klasörü kontrol et/oluştur.
        if not os.path.exists("barkodlar"):
            os.makedirs("barkodlar")

        self.vt_hazirla()            # Veritabanı tablolarını oluştur
        self.tum_ogrenciler = []     # RAM'de tutulacak öğrenci listesi
        self.arayuz_hazirla()        # Ana pencere bileşenlerini kur
        self.kayitlari_yukle()       # Kitapları tabloya çek
        self.ogrencileri_veritabanindan_cek()

    # SQLite Veritabanı ve Tablo İşlemleri
    def vt_hazirla(self):
        with sqlite3.connect("kutuphane.db") as baglanti:
            cursor = baglanti.cursor()
            # Kitaplar tablosu: Kitabın genel ve zimmet durumu bilgilerini tutar.
            cursor.execute("""CREATE TABLE IF NOT EXISTS kitaplar (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                isim TEXT, yazar TEXT, barkod_no TEXT, kategori TEXT,
                durum TEXT DEFAULT 'Mevcut', 
                zimmetli_kisi TEXT DEFAULT '-',
                alis_tarihi TEXT DEFAULT '-'
            )""")
            # Mevcut tabloya 'kategori' sütununu sonradan eklemek için (Hata yönetimli).
            try:
                cursor.execute("ALTER TABLE kitaplar ADD COLUMN kategori TEXT DEFAULT '-'")
            except: pass

            # Geçmiş ödünç alma kayıtlarını tutan tablo.
            cursor.execute("""CREATE TABLE IF NOT EXISTS odunc_kayitlari (
                id INTEGER PRIMARY KEY AUTOINCREMENT, kitap_id INTEGER, 
                ogrenci_adi TEXT, verilis_tarihi TEXT, teslim_tarihi TEXT, 
                iade_edildi INTEGER DEFAULT 0)""")
            
            # Excel'den yüklenen öğrenci bilgilerini tutan tablo.
            cursor.execute("CREATE TABLE IF NOT EXISTS ogrenciler (id INTEGER PRIMARY KEY AUTOINCREMENT, ogrenci_no TEXT, ad_soyad TEXT)")
            baglanti.commit()

    # Ana Arayüz Tasarımı
    def arayuz_hazirla(self):
        self.merkez_widget = QWidget()
        self.setCentralWidget(self.merkez_widget)
        self.ana_duzen = QVBoxLayout(self.merkez_widget)
        self.ana_duzen.setContentsMargins(40, 20, 40, 40)
        self.ana_duzen.setSpacing(20)

        # NAVBAR: Logo ve Genel Ayarlar
        navbar = QHBoxLayout()
        logo = QLabel("Kütüphane Takip Sistemi")
        logo.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a2a6c;")
        navbar.addWidget(logo)
        navbar.addStretch()
        
        btn_excel = self.modern_buton("Excel Yükle", "#f1c40f", "black")
        btn_excel.clicked.connect(self.excel_yukle)
        navbar.addWidget(btn_excel)
        self.ana_duzen.addLayout(navbar)

        # BAŞLIK VE ARAMA: Kullanıcıyı karşılayan alan ve hızlı arama çubuğu.
        header = QHBoxLayout()
        baslik_v = QVBoxLayout()
        lbl_m = QLabel("Kütüphane Takip Sistemi")
        lbl_m.setStyleSheet("font-size: 30px; font-weight: bold;")
        lbl_s = QLabel("Kitap, Barkod veya Kişi adına göre arama yapın.")
        lbl_s.setStyleSheet("color: #777;")
        baslik_v.addWidget(lbl_m)
        baslik_v.addWidget(lbl_s)
        
        self.txt_arama = QLineEdit()
        self.txt_arama.setPlaceholderText("Arama yapın...")
        self.txt_arama.setFixedWidth(350)
        self.txt_arama.setStyleSheet("border: 1px solid #ddd; border-radius: 8px; padding: 10px;")
        self.txt_arama.textChanged.connect(self.kayitlari_yukle) # Her harf değişiminde listeyi günceller.
        
        header.addLayout(baslik_v)
        header.addStretch()
        header.addWidget(self.txt_arama)
        self.ana_duzen.addLayout(header)

        # İŞLEM BUTONLARI: Ekle, Zimmetle ve İade Al.
        islem_bar = QHBoxLayout()
        self.lbl_ozet = QLabel("Koleksiyon Listesi")
        islem_bar.addWidget(self.lbl_ozet)
        islem_bar.addStretch()
        
        btn_ekle = self.modern_buton("+ Kitap Ekle", "#2ecc71", "white")
        btn_ekle.clicked.connect(self.kitap_ekle_penceresi_ac)
        
        btn_zimmet = self.modern_buton("Zimmetle", "#3498db", "white")
        btn_zimmet.clicked.connect(self.odunc_ver_dialog)
        
        btn_iade = self.modern_buton("İade Al", "#e67e22", "white")
        btn_iade.clicked.connect(self.iade_al)
        
        islem_bar.addWidget(btn_ekle)
        islem_bar.addWidget(btn_zimmet)
        islem_bar.addWidget(btn_iade)
        self.ana_duzen.addLayout(islem_bar)

        # TABLO SİSTEMİ: Verilerin listelendiği ana ızgara.
        self.tablo = QTableWidget()
        self.tablo.setColumnCount(8)
        self.tablo.setHorizontalHeaderLabels(["ID", "KİTAP ADI", "YAZAR", "BARKOD", "KATEGORİ", "DURUM", "ZİMMETLİ", "ALIŞ TARİHİ"])
        self.tablo.setSelectionBehavior(QTableWidget.SelectRows) 
        self.tablo.setSelectionMode(QTableWidget.SingleSelection)
        self.tablo.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setShowGrid(False)
        self.tablo.setStyleSheet("QTableWidget::item:selected { background-color: #1a2a6c; color: white; }")
        self.ana_duzen.addWidget(self.tablo)

    def modern_buton(self, t, bg, c):
        b = QPushButton(t)
        b.setStyleSheet(f"background-color: {bg}; color: {c}; border-radius: 6px; padding: 8px 15px; font-weight: bold;")
        b.setCursor(Qt.PointingHandCursor)
        return b

    # Veritabanındaki kitapları tabloya aktarır.
    def kayitlari_yukle(self):
        arama = self.txt_arama.text().lower()
        self.tablo.setRowCount(0)
        with sqlite3.connect("kutuphane.db") as baglanti:
            cursor = baglanti.cursor()
            # SQL LIKE sorgusu ile isim, barkod veya kişi bazlı arama yapılır.
            cursor.execute("""SELECT id, isim, yazar, barkod_no, kategori, durum, zimmetli_kisi, alis_tarihi 
                           FROM kitaplar WHERE lower(isim) LIKE ? OR lower(barkod_no) LIKE ? OR lower(zimmetli_kisi) LIKE ?""", 
                           (f'%{arama}%', f'%{arama}%', f'%{arama}%'))
            for i, satir in enumerate(cursor.fetchall()):
                self.tablo.insertRow(i)
                for j, veri in enumerate(satir):
                    item = QTableWidgetItem(str(veri))
                    # Durum sütunu (Mevcut/Zimmetli) için renklendirme.
                    if j == 5: 
                        item.setForeground(QColor("#27ae60" if veri == "Mevcut" else "#e67e22"))
                    self.tablo.setItem(i, j, item)

    # Yeni kitap eklerken aynı zamanda rastgele EAN-13 barkodu üretir.
    def kitap_ekle_penceresi_ac(self):
        pencere = KitapEklePenceresi(self)
        if pencere.exec_():
            ad, yazar, kategori = pencere.verileri_al()
            if ad and yazar:
                with sqlite3.connect("kutuphane.db") as baglanti:
                    cursor = baglanti.cursor()
                    cursor.execute("INSERT INTO kitaplar (isim, yazar, kategori) VALUES (?, ?, ?)", (ad, yazar, kategori))
                    k_id = cursor.lastrowid
                    
                    # 12 haneli rastgele sayı üretilir
                    b_no = "".join([str(random.randint(0, 9)) for _ in range(12)])
                    
                    # --- DOSYA ADI OLUŞTURMA (KitapAdı_YazarAdı) ---
                    # Geçersiz karakterleri temizleme fonksiyonu (/, \, *, ?, ", <, >, | gibi karakterleri siler)
                    def temizle(metin):
                        return "".join([c for c in metin if c.isalnum()]).strip()

                    temiz_ad = temizle(ad)
                    temiz_yazar = temizle(yazar)
                    dosya_adi = f"{temiz_ad}_{temiz_yazar}"
                    
                    # Barkodu "KitapAdı_YazarAdı" formatında kaydet
                    barcode.get_barcode_class('ean13')(b_no, writer=ImageWriter()).save(f"barkodlar/{dosya_adi}")
                    # -----------------------------------------------

                    cursor.execute("UPDATE kitaplar SET barkod_no = ? WHERE id = ?", (b_no + "0", k_id))
                self.kayitlari_yukle()
            else:
                QMessageBox.warning(self, "Hata", "Kitap adı ve yazar boş bırakılamaz!")

    # Excel dosyasından öğrenci listesini topluca veritabanına aktarır.
    def excel_yukle(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Excel Seç", "", "Excel Files (*.xlsx *.xls)")
        if yol:
            try:
                df = pd.read_excel(yol)
                with sqlite3.connect("kutuphane.db") as baglanti:
                    cursor = baglanti.cursor()
                    cursor.execute("DELETE FROM ogrenciler")
                    for _, r in df.iterrows():
                        cursor.execute("INSERT INTO ogrenciler (ogrenci_no, ad_soyad) VALUES (?,?)", 
                                       (str(r.iloc[0]), str(r.iloc[1])))
                self.ogrencileri_veritabanindan_cek()
                QMessageBox.information(self, "Başarılı", "Öğrenci listesi güncellendi.")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Excel yüklenirken hata oluştu: {str(e)}")

    # Öğrencileri veritabanından çekip arama listesine hazır hale getirir.
    def ogrencileri_veritabanindan_cek(self):
        with sqlite3.connect("kutuphane.db") as baglanti:
            cursor = baglanti.cursor()
            cursor.execute("SELECT ogrenci_no, ad_soyad FROM ogrenciler")
            self.tum_ogrenciler = [f"{s[0]} - {s[1]}" for s in cursor.fetchall()]

    # Kitabı ödünç verme (zimmetleme) süreci.
    def odunc_ver_dialog(self):
        secili = self.tablo.currentRow()
        if secili < 0:
            QMessageBox.warning(self, "Hata", "Lütfen önce tablodan bir kitap seçin!")
            return
        
        k_id = self.tablo.item(secili, 0).text()
        durum = self.tablo.item(secili, 5).text()
        
        if durum != "Mevcut":
            QMessageBox.warning(self, "Hata", "Kitap zaten ödünç verilmiş!")
            return

        if not self.tum_ogrenciler:
            QMessageBox.warning(self, "Hata", "Öğrenci listesi boş! Lütfen önce Excel yükleyin.")
            return

        pencere = ZimmetlePenceresi(self.tum_ogrenciler, self)
        if pencere.exec_():
            secilen = pencere.secilen_ogrenci()
            if secilen:
                bugun = datetime.now().strftime("%Y-%m-%d")
                teslim = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d") # 15 gün süre tanır.
                
                with sqlite3.connect("kutuphane.db") as baglanti:
                    cursor = baglanti.cursor()
                    cursor.execute("UPDATE kitaplar SET durum='Zimmetli', zimmetli_kisi=?, alis_tarihi=? WHERE id=?", (secilen, bugun, k_id))
                    cursor.execute("INSERT INTO odunc_kayitlari (kitap_id, ogrenci_adi, verilis_tarihi, teslim_tarihi) VALUES (?,?,?,?)", (k_id, secilen, bugun, teslim))
                
                self.kayitlari_yukle()
                QMessageBox.information(self, "Başarılı", f"Kitap başarıyla {secilen} kişisine zimmetlendi.")

    # Kitabı geri alma ve durumunu 'Mevcut' olarak güncelleme.
    def iade_al(self):
        secili = self.tablo.currentRow()
        if secili < 0: return
        k_id = self.tablo.item(secili, 0).text()
        with sqlite3.connect("kutuphane.db") as baglanti:
            cursor = baglanti.cursor()
            cursor.execute("UPDATE kitaplar SET durum='Mevcut', zimmetli_kisi='-', alis_tarihi='-' WHERE id=?", (k_id,))
            cursor.execute("UPDATE odunc_kayitlari SET iade_edildi=1 WHERE kitap_id=? AND iade_edildi=0", (k_id,))
        self.kayitlari_yukle()

# Uygulama Başlatıcı
if __name__ == "__main__":
    app = QApplication(sys.argv)
    pencere = KutuphaneUygulamasi()
    pencere.show()
    sys.exit(app.exec_())