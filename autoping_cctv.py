import pandas as pd
import subprocess
import platform
import time
import os
import concurrent.futures
from datetime import datetime

# ==========================================
# BAHAGIAN TETAPAN UTAMA
# ==========================================
NAMA_FAIL_MASTER = 'master_data.csv'         
NAMA_LAJUR_IP = 'IP Adddress'                
NAMA_FAIL_OUTPUT = 'Data_Dashboard_CCTV.csv' 

# DIKURANGKAN KEPADA 10 UNTUK KESELAMATAN RANGKAIAN (Cybersecurity Friendly)
MAKSIMUM_PEKERJA = 10  

LAJUR_DIPERLUKAN = [
    'Site Name', 'Device Type', 'Brand', 'Model', 
    'S/N', 'Device Name', 'MAC Address', 'IP Adddress', 'Location'
]
# ==========================================

def ping_ip_senyap(ip_address):
    """Melakukan proses ping pada satu IP."""
    if pd.isna(ip_address) or str(ip_address).strip() == "":
        return "Tiada IP"
    ip_str = str(ip_address).strip()
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    # Timeout ditingkatkan sedikit ke 1000ms untuk kestabilan dalam 10 thread
    command = ['ping', param, '1', '-w', '1000', ip_str]
    try:
        response = subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        return "Online" if response == 0 else "Offline"
    except Exception:
        return "Error"

def jalankan_kitaran(kitaran_ke):
    waktu_sekarang = datetime.now()
    masa_waktu_ini = waktu_sekarang.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n" + "="*60)
    print(f" KITARAN {kitaran_ke} | DIMULAKAN PADA: {masa_waktu_ini}")
    print("="*60)
    
    # 1. BACA MASTER DATA
    try:
        df = pd.read_csv(NAMA_FAIL_MASTER, encoding='cp1252')
        df = df.dropna(subset=[NAMA_LAJUR_IP]) 
    except Exception as e:
        print(f"[RALAT] Fail '{NAMA_FAIL_MASTER}' tidak ditemui atau format salah: {e}")
        return
        
    # 2. BACA SEJARAH LAMA (Untuk memori Incident_Count)
    sejarah_cctv = {}
    if os.path.exists(NAMA_FAIL_OUTPUT):
        try:
            df_lama = pd.read_csv(NAMA_FAIL_OUTPUT)
            for _, row in df_lama.iterrows():
                ip_rekod = str(row.get(NAMA_LAJUR_IP, '')).strip()
                sejarah_cctv[ip_rekod] = {
                    'status_lama': row.get('Status_Terkini', 'Online'),
                    'waktu_mula_offline': row.get('Waktu_Mula_Offline', ''),
                    'incident_count': row.get('Incident_Count', 0)
                }
        except Exception:
            pass # Jika fail baru, biarkan sejarah kosong

    senarai_ip = [str(ip).strip() for ip in df[NAMA_LAJUR_IP].tolist()]
    jumlah_ip = len(senarai_ip)
    
    # 3. PROSES PING (DENGAN PAPARAN PROGRESS LIVE)
    print(f"Menyemak {jumlah_ip} peranti menggunakan {MAKSIMUM_PEKERJA} thread...")
    
    # Kita gunakan ThreadPoolExecutor untuk kelajuan
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAKSIMUM_PEKERJA) as executor:
        keputusan_ping = list(executor.map(ping_ip_senyap, senarai_ip))
    
    # 4. PROSES LOGIK & PAPARAN HASIL KE COMMAND PROMPT
    status_baru_list = []
    waktu_offline_list = []
    tempoh_downtime_list = []
    incident_count_list = []
    
    print("-" * 60)
    print(f"{'BIL':<4} | {'ALAMAT IP':<15} | {'STATUS':<8} | {'INCIDENT':<10}")
    print("-" * 60)

    for i, (ip_str, status_baru) in enumerate(zip(senarai_ip, keputusan_ping), 1):
        data_lama = sejarah_cctv.get(ip_str, {})
        status_lama = data_lama.get('status_lama', 'Online')
        count_lama = data_lama.get('incident_count', 0)
        waktu_mula_off_lama = data_lama.get('waktu_mula_offline', '')

        # LOGIK INCIDENT: Jika status berubah dari Online ke Offline
        if status_lama == "Online" and status_baru == "Offline":
            count_baru = int(count_lama) + 1
        else:
            count_baru = int(count_lama)

        # LOGIK DOWNTIME
        if status_baru == "Offline":
            if status_lama == "Offline" and pd.notna(waktu_mula_off_lama) and str(waktu_mula_off_lama).strip() != "":
                rekod_waktu_off = str(waktu_mula_off_lama)
                try:
                    mula_dt = pd.to_datetime(rekod_waktu_off)
                    tempoh = str(waktu_sekarang - mula_dt).split('.')[0]
                except:
                    tempoh = "Gagal kira"
            else:
                rekod_waktu_off = masa_waktu_ini
                tempoh = "Baru terputus"
        else:
            rekod_waktu_off = ""
            tempoh = "-"
            
        # Paparkan progress di Command Prompt
        print(f"{i:<4} | {ip_str:<15} | {status_baru:<8} | {count_baru:<10}")

        status_baru_list.append(status_baru)
        waktu_offline_list.append(rekod_waktu_off)
        tempoh_downtime_list.append(tempoh)
        incident_count_list.append(count_baru)

    # 5. KEMASKINI & SIMPAN FAIL
    df['Status_Terkini'] = status_baru_list
    df['Waktu_Semakan_Terakhir'] = masa_waktu_ini
    df['Waktu_Mula_Offline'] = waktu_offline_list
    df['Tempoh_Downtime'] = tempoh_downtime_list
    df['Incident_Count'] = incident_count_list
    
    lajur_akhir = LAJUR_DIPERLUKAN + ['Status_Terkini', 'Waktu_Semakan_Terakhir', 'Waktu_Mula_Offline', 'Tempoh_Downtime', 'Incident_Count']
    df_bersih = df[[col for col in lajur_akhir if col in df.columns]]
    
    try:
        df_bersih.to_csv(NAMA_FAIL_OUTPUT, index=False)
        print("-" * 60)
        print(f"SUCCESS: Data disimpan ke '{NAMA_FAIL_OUTPUT}'")
    except PermissionError:
        print("\n[!] AMARAN: Sila tutup fail 'Data_Dashboard_CCTV.csv' di Excel supaya data boleh disimpan.")

def main():
    print("="*60)
    print("   SISTEM MONITORING CCTV - VERSI ANALISIS INSIDEN")
    print("="*60)
    
    try:
        h = input("Set Jarak Masa (Jam)   : ").strip() or "0"
        m = input("Set Jarak Masa (Minit) : ").strip() or "1"
        s = input("Set Jarak Masa (Saat)  : ").strip() or "0"

        saat_menunggu = (int(h) * 3600) + (int(m) * 60) + int(s)
        if saat_menunggu == 0: saat_menunggu = 60
    except ValueError:
        print("Input salah, sistem akan berjalan setiap 60 saat secara default.")
        saat_menunggu = 60
    
    kitaran = 1
    try:
        while True:
            jalankan_kitaran(kitaran)
            print(f"\nMenunggu {saat_menunggu} saat untuk kitaran seterusnya (Ctrl+C untuk berhenti)...")
            time.sleep(saat_menunggu)
            kitaran += 1
    except KeyboardInterrupt:
        print("\n\nSistem diberhentikan. Terima kasih.")

if __name__ == "__main__":
    main()