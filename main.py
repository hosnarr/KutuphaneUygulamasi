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


default_scroll_sheet = """
    /* Ana Arka Plan */
    QMainWindow { background-color: #ffffff; }

    /* Dikey Scrollbar Tasarımı */
    QScrollBar:vertical {
        border: none;
        background: #f1f1f1;
        width: 10px;
        margin: 0px 0px 0px 0px;
        border-radius: 5px;
    }

    /* Kaydırma Çubuğunun Hareket Eden Kısmı (Handle) */
    QScrollBar::handle:vertical {
        background: #bbb;
        min-height: 30px;
        border-radius: 5px;
    }

    /* Mouse Üzerine Geldiğinde Handle Rengi */
    QScrollBar::handle:vertical:hover {
        background: #888;
    }

    /* Scrollbar Ok Tuşlarını Gizle (Modern görünüm için) */
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        border: none;
        background: none;
        height: 0px;
    }

    /* Yatay Scrollbar Tasarımı (Gerekirse) */
    QScrollBar:horizontal {
        border: none;
        background: #f1f1f1;
        height: 10px;
        border-radius: 5px;
    }

    QScrollBar::handle:horizontal {
        background: #bbb;
        min-width: 30px;
        border-radius: 5px;
    }

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        border: none;
        background: none;
        width: 0px;
    }
"""

# --- ZİMMETLEME PENCERESİ ---
# Bu sınıf, bir kitabı belirli bir öğrenciye atamak (ödünç vermek) için açılan küçük penceredir.
class ZimmetlePenceresi(QDialog):
    def __init__(self, ogrenci_listesi, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kitap Zimmetle")
        self.setFixedWidth(450)
        self.setFixedHeight(500)
        # CSS benzeri StyleSheet ile modern bir görünüm kazandırıyoruz.
        self.setStyleSheet(default_scroll_sheet)
        
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
        self.setStyleSheet(default_scroll_sheet)
        
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
        self.setStyleSheet(default_scroll_sheet)
        
        # Barkod görsellerinin kaydedileceği klasörü kontrol et/oluştur.
        if not os.path.exists("barkodlar"):
            os.makedirs("barkodlar")

        self.vt_hazirla()            # Veritabanı tablolarını oluştur
        self.tum_ogrenciler = []     # RAM'de tutulacak öğrenci listesi
        self.arayuz_hazirla()        # Ana pencere bileşenlerini kur
        self.kayitlari_yukle()       # Kitapları tabloya çek
        self.ogrencileri_veritabanindan_cek()

    # Seçilen kitabı veritabanından siler ve ilgili barkod dosyasını da kaldırır.
    def kitap_sil(self):
        secili_satir = self.tablo.currentRow()
        
        if secili_satir < 0:
            QMessageBox.warning(self, "Hata", "Lütfen silmek istediğiniz kitabı tablodan seçin!")
            return

        # Gizli veriden Gerçek ID'yi ve tablodan Kitap Adı/Yazar bilgilerini alıyoruz
        k_id = self.tablo.item(secili_satir, 0).data(Qt.UserRole)
        k_adi = self.tablo.item(secili_satir, 1).text()
        yazar_adi = self.tablo.item(secili_satir, 2).text() # Yazar adını da alıyoruz

        cevap = QMessageBox.question(self, "Silme Onayı", 
                                    f"'{k_adi}' isimli kitabı ve barkod dosyasını silmek istediğinize emin misiniz?",
                                    QMessageBox.Yes | QMessageBox.No)

        if cevap == QMessageBox.Yes:
            try:
                # --- DOSYA SİLME İŞLEMİ ---
                def temizle(metin):
                    return "".join([c for c in metin if c.isalnum()]).strip()

                # Barkod oluştururken kullandığımız aynı isimlendirme formatı:
                dosya_adi = f"{temizle(k_adi)}_{temizle(yazar_adi)}.png"
                dosya_yolu = os.path.join("barkodlar", dosya_adi)

                if os.path.exists(dosya_yolu):
                    os.remove(dosya_yolu)
                # --------------------------

                with sqlite3.connect("kutuphane.db") as baglanti:
                    cursor = baglanti.cursor()
                    cursor.execute("DELETE FROM kitaplar WHERE id = ?", (k_id,))
                    cursor.execute("DELETE FROM odunc_kayitlari WHERE kitap_id = ?", (k_id,))
                    baglanti.commit()
                
                self.kayitlari_yukle()
                self.istatistikleri_guncelle() # Sayaçları da yenilemiş oluyoruz
                QMessageBox.information(self, "Başarılı", "Kitap ve barkod dosyası başarıyla silindi.")
                
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Silme işlemi sırasında bir hata oluştu: {str(e)}")


    # kitaplerı bu fonsiyon ile topluca ekleriz. Excel dosyasındaki her satır için kitap kaydı oluşturur ve barkod üretir.
    def kitap_excel_yukle(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Kitap Listesi Seç", "", "Excel Files (*.xlsx *.xls)")
        if yol:
            try:
                df = pd.read_excel(yol)
                # Sütun isimlerini standartlaştıralım (Opsiyonel: Eğer Excel başlıkları farklıysa index kullanırız)
                with sqlite3.connect("kutuphane.db") as baglanti:
                    cursor = baglanti.cursor()
                    
                    eklenen_sayisi = 0
                    for _, r in df.iterrows():
                        # Sütunları güvenli bir şekilde alalım (A=0, B=1, C=2)
                        ad = str(r.iloc[0]) if pd.notnull(r.iloc[0]) else None
                        yazar = str(r.iloc[1]) if pd.notnull(r.iloc[1]) else None
                        # Kategori boşsa '-' ata
                        kategori = str(r.iloc[2]) if len(r) > 2 and pd.notnull(r.iloc[2]) else "-"

                        if ad and yazar:
                            # Veritabanına ekle
                            cursor.execute("INSERT INTO kitaplar (isim, yazar, kategori) VALUES (?, ?, ?)", 
                                           (ad, yazar, kategori))
                            k_id = cursor.lastrowid

                            # Barkod üretimi
                            b_no = "".join([str(random.randint(0, 9)) for _ in range(12)])
                            
                            def temizle(metin):
                                return "".join([c for c in metin if c.isalnum()]).strip()

                            dosya_adi = f"{temizle(ad)}_{temizle(yazar)}"
                            barcode.get_barcode_class('ean13')(b_no, writer=ImageWriter()).save(f"barkodlar/{dosya_adi}")

                            # Barkod numarasını (checksum dahil) güncelle
                            cursor.execute("UPDATE kitaplar SET barkod_no = ? WHERE id = ?", (b_no + "0", k_id))
                            eklenen_sayisi += 1
                    
                    baglanti.commit()
                
                self.kayitlari_yukle()
                QMessageBox.information(self, "Başarılı", f"{eklenen_sayisi} adet kitap başarıyla yüklendi ve barkodları oluşturuldu.")
            
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Kitap listesi yüklenirken hata oluştu: {str(e)}")

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

        btn_kitap_excel = self.modern_buton("Kitap Excel Yükle", "#9b59b6", "white") # Mor renkli buton
        btn_kitap_excel.clicked.connect(self.kitap_excel_yukle)
        navbar.addWidget(btn_kitap_excel)

        # BAŞLIK VE ÖZET BİLGİLER
        header = QHBoxLayout()
        baslik_v = QVBoxLayout()
        
        lbl_m = QLabel("Kütüphane Takip Sistemi")
        lbl_m.setStyleSheet("font-size: 28px; font-weight: bold; color: #1a2a6c;")
        
        # İstatistik Satırı
        istatistik_layout = QHBoxLayout()
        istatistik_layout.setSpacing(20)

        # Toplam Kitap Sayacı
        self.lbl_toplam_kitap = QLabel("📚 Toplam Kitap: 0")
        self.lbl_toplam_kitap.setStyleSheet("font-size: 14px; color: #555; background: #f0f2f5; padding: 5px 12px; border-radius: 15px;")
        
        # Toplam Öğrenci Sayacı
        self.lbl_toplam_ogrenci = QLabel("👤 Toplam Öğrenci: 0")
        self.lbl_toplam_ogrenci.setStyleSheet("font-size: 14px; color: #555; background: #f0f2f5; padding: 5px 12px; border-radius: 15px;")

        istatistik_layout.addWidget(self.lbl_toplam_kitap)
        istatistik_layout.addWidget(self.lbl_toplam_ogrenci)
        istatistik_layout.addStretch() # Yazıları sola yaslar

        baslik_v.addWidget(lbl_m)
        baslik_v.addLayout(istatistik_layout)
        
        # Arama Kutusu (Sağ tarafta kalmaya devam ediyor)
        self.txt_arama = QLineEdit()
        self.txt_arama.setPlaceholderText("Hızlı arama...")
        self.txt_arama.setFixedWidth(300)
        self.txt_arama.setStyleSheet("border: 1px solid #ddd; border-radius: 20px; padding: 10px 15px;")
        self.txt_arama.textChanged.connect(self.kayitlari_yukle)
        
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

        btn_sil = self.modern_buton("Kitabı Sil", "#e74c3c", "white") # Kırmızı renk
        btn_sil.clicked.connect(self.kitap_sil)
    
        
        islem_bar.addWidget(btn_ekle)
        islem_bar.addWidget(btn_zimmet)
        islem_bar.addWidget(btn_iade)
        islem_bar.addWidget(btn_sil)
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

    # Veritabanından kitap kayıtlarını çekip tabloya yükler. Arama kutusundaki metne göre filtreleme yapar.
    def kayitlari_yukle(self):
        arama = self.txt_arama.text().lower()
        self.tablo.setRowCount(0)
        with sqlite3.connect("kutuphane.db") as baglanti:
            cursor = baglanti.cursor()
            # ID'yi hala çekiyoruz (arka planda silme/güncelleme için lazım) ama ekranda göstermeyeceğiz
            cursor.execute("""SELECT id, isim, yazar, barkod_no, kategori, durum, zimmetli_kisi, alis_tarihi 
                           FROM kitaplar WHERE lower(isim) LIKE ? OR lower(barkod_no) LIKE ? OR lower(zimmetli_kisi) LIKE ?""", 
                           (f'%{arama}%', f'%{arama}%', f'%{arama}%'))
            
            veriler = cursor.fetchall()
            for i, satir in enumerate(veriler):
                self.tablo.insertRow(i)
                
                # --- SIRALAMA SİSTEMİ BURADA BAŞLIYOR ---
                # Gerçek ID yerine satır indeksinin 1 fazlasını (i+1) yazdırıyoruz
                sira_no_item = QTableWidgetItem(str(i + 1))
                sira_no_item.setTextAlignment(Qt.AlignCenter) # Ortaya hizalayalım, şık dursun
                
                # Veritabanındaki GERÇEK ID'yi gizli bir veri (UserRole) olarak saklıyoruz 
                # Böylece silme butonu hangi ID'yi sileceğini hala bilecek
                sira_no_item.setData(Qt.UserRole, str(satir[0])) 
                
                self.tablo.setItem(i, 0, sira_no_item)
                # ----------------------------------------

                # Diğer sütunları (1'den başlayarak) doldurmaya devam et
                for j in range(1, len(satir)):
                    veri = satir[j]
                    item = QTableWidgetItem(str(veri))
                    if j == 5: # Durum sütunu renklendirmesi
                        item.setForeground(QColor("#27ae60" if veri == "Mevcut" else "#e67e22"))
                    self.tablo.setItem(i, j, item)
                    self.istatistikleri_guncelle()

    # Kitap ve öğrenci istatistiklerini günceller. Toplam kitap sayısı ve toplam öğrenci sayısını ekranda gösterir.
    def istatistikleri_guncelle(self):
        try:
            with sqlite3.connect("kutuphane.db") as baglanti:
                cursor = baglanti.cursor()
                
                # Kitap sayısını al
                cursor.execute("SELECT COUNT(*) FROM kitaplar")
                kitap_sayisi = cursor.fetchone()[0]
                
                # Öğrenci sayısını al
                cursor.execute("SELECT COUNT(*) FROM ogrenciler")
                ogrenci_sayisi = cursor.fetchone()[0]
                
                # Ekrana yazdır
                self.lbl_toplam_kitap.setText(f"📚 Toplam Kitap: {kitap_sayisi}")
                self.lbl_toplam_ogrenci.setText(f"👤 Toplam Öğrenci: {ogrenci_sayisi}")
                
        except Exception as e:
            print(f"İstatistik hatası: {e}")



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
        self.istatistikleri_guncelle()


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
            self.istatistikleri_guncelle()


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