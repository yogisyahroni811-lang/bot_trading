Sentinel-X Master Blueprint: Personal High-Alpha Edition

1. Filosofi Inti: "Disiplin di Atas Inteligensia"

Sistem ini tidak dibangun untuk menjadi "pintar" (menebak masa depan), melainkan untuk menjadi "filternya filter." AI (LLM) hanya digunakan untuk memahami narasi market yang tidak bisa dibaca oleh matematika tradisional, namun matematika tetap memegang kendali eksekusi.



2. Arsitektur Hirarki Keputusan (The Judge 2.0)

Agar AI tidak mengalami bias konfirmasi, kita menerapkan Hierarchical Decision Matrix dengan bobot yang tidak bisa diganggu gugat.



A. Tier 1: Struktur & Makro (Bobot 50%)

Sumber: Matematika (Moving Averages, Market Structure High/Low).

Logika: Jika H4 Bearish, skor Tier 1 otomatis -1. AI dilarang mencari setup "Buy" meski indikator lain mendukung.

B. Tier 2: Area & Likuiditas (Bobot 30%)

Sumber: RAG (Strategi Supply/Demand, Order Blocks).

Logika: Apakah harga berada di area yang secara historis memiliki probabilitas tinggi?

C. Tier 3: Trigger & Konfirmasi (Bobot 20%)

Sumber: AI Narrative Analysis.

Logika: Analisis pola candlestick dan momentum jangka pendek (M15/M5).

3. Fitur "Advisors Audit" (Mencegah Blind Spots)

Fitur 1: Adversarial Reasoning (Devil's Advocate)

Sebelum eksekusi, sistem menjalankan dua agen AI:



Agen Pro: Mencari alasan kenapa trade ini akan profit.

Agen Kontra: Tugasnya adalah "menghancurkan" setup tersebut. Dia harus mencari alasan kenapa trade ini akan gagal (misal: "Ada liquidity grab di atas," atau "Ini adalah jebakan retail").

The Judge: Hanya akan mengeksekusi jika argumen Agen Kontra terbukti lemah secara statistik.

Fitur 2: Reasoning Transparency Log

Setiap keputusan disimpan dalam file Markdown. Kamu wajib membacanya setiap akhir pekan. Jika bot rugi dan alasannya "ngawur," kamu harus langsung memperbaiki database RAG kamu.



Fitur 3: Prop Firm Hard-Coded Guardrails

Daily Loss Limit: Terkunci di level kernel (Rust/Tauri). Jika minus 4%, sistem mati total.

News Grounding: Integrasi kalender ekonomi otomatis. Bot berhenti 30 menit sebelum/setudah berita High Impact.

Virtual SL/TP: Parameter tidak dikirim ke broker untuk menghindari manipulasi, namun dieksekusi secara lokal secepat kilat (gRPC).

4. Rencana Implementasi (Prioritas Strategis)

Tahap 1: Evaluasi Strategi (Minggu 1) - KRUSIAL

Jangan tulis kode. Tulis 10 aturan baku strategimu di kertas. Jika aturan ini tidak bisa kamu jelaskan secara logis kepada anak kecil, AI akan mengacaukannya.Opportunity Cost: Melewatkan tahap ini berarti menghabiskan 2 bulan coding untuk sistem yang akan meledak di hari pertama.



Tahap 2: Fondasi Data (Minggu 2-3)

Bangun gRPC bridge antara MT5 dan Python.

Setup ChromaDB (Vector Store). Masukkan hanya strategi yang sudah terbukti (Proven). Jangan masukkan "sampah" internet.

Tahap 3: Logic Wrapping (Minggu 4-5)

Implementasi DecisionMatrix dan agen Adversarial Reasoning.

Testing di akun Demo dengan skenario market yang paling buruk.

Tahap 4: Desktop Bundling (Minggu 6+)

Wrapping menggunakan Tauri sebagai Sidecar.

Pastikan enkripsi API Key aman di level sistem operasi.
