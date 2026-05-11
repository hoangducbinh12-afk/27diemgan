import streamlit as st
import easyocr
import pandas as pd
import json
import numpy as np
from PIL import Image

# --- HẰNG SỐ HIỆU QUY ƯỚC ---
HIEU_CHART = {0: [0,11,22,33,44,55,66,77,88,99], 1: [9,10,21,32,43,54,65,76,87,98],
              2: [8,19,20,31,42,53,64,75,86,97], 3: [7,18,29,30,41,52,63,74,85,96],
              4: [6,17,28,39,40,51,62,73,84,95], 5: [5,16,27,38,49,50,61,72,83,94],
              6: [4,15,26,37,48,59,60,71,82,93], 7: [3,14,25,36,47,58,69,70,81,92],
              8: [2,13,24,35,46,57,68,79,80,91], 9: [1,12,23,34,45,56,67,78,89,90]}

st.set_page_config(page_title="App Săn Gan Cao Cấp", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = {"bang_b_points": [], "current_raw": [], "history": []}

if st.sidebar.button("❌ KHÔI PHỤC TẤT CẢ", use_container_width=True):
    st.session_state.db = {"bang_b_points": [], "current_raw": [], "history": []}
    st.rerun()

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'])

def analyze_number(num):
    s = f"{num:02d}"
    x, y = int(s[0]), int(s[1])
    h_val = next((h for h, nums in HIEU_CHART.items() if num in nums), 0)
    return {"dau": x, "duoi": y, "tong": (x + y) % 10, "hieu": h_val, "cham": [x, y]}

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Cấu hình Săn Gan")
    uploaded_file = st.file_uploader("1. Tải kết quả bảng ảnh", type=["png", "jpg", "jpeg"])
    uploaded_json = st.file_uploader("📂 Tìm kiếm dữ liệu cũ", type=["json"])
    if uploaded_json:
        st.session_state.db = json.load(uploaded_json)
    run_btn = st.button("🚀 CẬP NHẬT TỔNG LỰC", use_container_width=True)

# --- XỬ LÝ LOGIC ---
if uploaded_file and run_btn:
    reader = load_ocr()
    image = Image.open(uploaded_file)
    results = reader.readtext(np.array(image), detail=0)
    
    all_loto = []
    all_digits_list = []
    for text in results:
        clean_text = "".join([d for d in text if d.isdigit()])
        if len(clean_text) >= 2:
            all_loto.append(int(clean_text[-2:]))
            for digit in clean_text: all_digits_list.append(int(digit))
    
    all_loto = all_loto[:27] 

    if len(all_loto) >= 1:
        raw = all_digits_list
        gdb_2_so = all_loto[0]
        
        # Thống kê hiệu quả dựa trên dàn cũ
        n10, n20, n30, n40, n50, rank_val, loai_val = ["N/A"]*7

        if st.session_state.db["current_raw"] and st.session_state.db["bang_b_points"]:
            old_raw, old_pts = st.session_state.db["current_raw"], st.session_state.db["bang_b_points"]
            df_temp = pd.DataFrame([{"S": old_raw[i], **old_pts[i]} for i in range(len(old_raw))])
            
            # Bảng C Săn Gan (>0)
            list_c_temp = []
            for i in range(10):
                m = df_temp[df_temp["S"] == i]
                list_c_temp.append({
                    "S":i, "d":m.loc[m["dau"]>0, "dau"].sum(), "đ":m.loc[m["duoi"]>0, "duoi"].sum(),
                    "t":m.loc[m["tong"]>0, "tong"].sum(), "h":m.loc[m["hieu"]>0, "hieu"].sum(), "c":m.loc[m["cham"]>0, "cham"].sum()
                })
            df_c_temp = pd.DataFrame(list_c_temp)
            
            dan_scores = []
            for i in range(100):
                t = analyze_number(i)
                score = df_c_temp.iloc[t["dau"]]["d"] + df_c_temp.iloc[t["duoi"]]["đ"] + df_c_temp.iloc[t["tong"]]["t"] + df_c_temp.iloc[t["hieu"]]["h"]
                score += (df_c_temp.iloc[t["dau"]]["c"] * 2) if t["dau"]==t["duoi"] else (df_c_temp.iloc[t["dau"]]["c"] + df_c_temp.iloc[t["duoi"]]["c"])
                dan_scores.append({"SO": f"{i:02d}", "DIEM": score})
            
            df_rank = pd.DataFrame(dan_scores).sort_values("DIEM", ascending=False).reset_index(drop=True)
            
            rank_f = df_rank[df_rank["SO"] == f"{gdb_2_so:02d}"].index
            if len(rank_f) > 0:
                rank_val = int(rank_f[0]) + 1
                loai_val = "A" if rank_val <= 70 else "T"
            
            # Thống kê nổ các dàn
            def count_hits(n): return f"{sum(1 for l in all_loto if f'{l:02d}' in df_rank.head(n)['SO'].tolist())}/{n}"
            n10, n20, n30, n40, n50 = count_hits(10), count_hits(20), count_hits(30), count_hits(40), count_hits(50)

        # Cập nhật điểm Bảng B
        targets = [analyze_number(n) for n in all_loto]
        s_dau, s_duoi, s_tong, s_hieu = {t["dau"] for t in targets}, {t["duoi"] for t in targets}, {t["tong"] for t in targets}, {t["hieu"] for t in targets}
        s_cham = set(); [s_cham.update(t["cham"]) for t in targets]

        if not st.session_state.db["current_raw"]:
            st.session_state.db["bang_b_points"] = [{"dau":1,"duoi":1,"tong":1,"hieu":1,"cham":1} for _ in range(len(raw))]
        else:
            pts_db, old_raw_db = st.session_state.db["bang_b_points"], st.session_state.db["current_raw"]
            for i in range(min(len(old_raw_db), len(pts_db))):
                val, p = old_raw_db[i], pts_db[i]
                p["dau"] = 0 if val in s_dau else p["dau"] + 1
                p["duoi"] = 0 if val in s_duoi else p["duoi"] + 1
                p["tong"] = 0 if val in s_tong else p["tong"] + 1
                p["hieu"] = 0 if val in s_hieu else p["hieu"] + 1
                p["cham"] = 0 if val in s_cham else p["cham"] + 1

        # Lưu Lịch sử
        st.session_state.db["history"].insert(0, {
            "Kỳ": len(st.session_state.db["history"]) + 1, "GĐB": f"{gdb_2_so:02d}", 
            "Vị trí": rank_val, "Loại": loai_val, 
            "Nổ 10": n10, "Nổ 20": n20, "Nổ 30": n30, "Nổ 40": n40, "Nổ 50": n50
        })
        st.session_state.db["current_raw"] = raw
        st.session_state.db["last_27"] = all_loto
        st.success(f"Đã cập nhật 27 giải. GĐB: {gdb_2_so:02d}")

# --- HIỂN THỊ ---
if st.session_state.db.get("current_raw"):
    if "last_27" in st.session_state.db:
        l = st.session_state.db["last_27"]
        st.write(f"**Giải Đặc Biệt:** `{l[0]:02d}` | **26 Giải Lô:** {', '.join([f'{x:02d}' for x in l[1:]])}")

    raw, pts = st.session_state.db["current_raw"], st.session_state.db["bang_b_points"]
    df_b = pd.DataFrame([{"SO VE": raw[i], **pts[i]} for i in range(len(raw))])
    
    list_c = []
    for i in range(10):
        m = df_b[df_b["SO VE"] == i]
        list_c.append({"S": i, "T ĐẦU": m.loc[m["dau"]>0, "dau"].sum(), "T ĐUÔI": m.loc[m["duoi"]>0, "duoi"].sum(), "T TỔNG": m.loc[m["tong"]>0, "tong"].sum(), "T HIỆU": m.loc[m["hieu"]>0, "hieu"].sum(), "T CHẠM": m.loc[m["cham"]>0, "cham"].sum()})
    df_c = pd.DataFrame(list_c)

    dan_f = []
    for i in range(100):
        t = analyze_number(i)
        score = df_c.iloc[t["dau"]]["T ĐẦU"] + df_c.iloc[t["duoi"]]["T ĐUÔI"] + df_c.iloc[t["tong"]]["T TỔNG"] + df_c.iloc[t["hieu"]]["T HIỆU"]
        score += (df_c.iloc[t["dau"]]["T CHẠM"] * 2) if t["dau"]==t["duoi"] else (df_c.iloc[t["dau"]]["T CHẠM"] + df_c.iloc[t["duoi"]]["T CHẠM"])
        dan_f.append({"SO": f"{i:02d}", "DIEM": int(score)})
    
    df_dan = pd.DataFrame(dan_f).sort_values("DIEM", ascending=False)

    st.write("### 🔥 DÀN SĂN GAN (CAO ➡️ THẤP)")
    c1, c2 = st.columns(2)
    with c1:
        num1 = st.number_input("Số quân Dàn 1:", 1, 100, 49)
        st.text_area("Dàn săn gan:", value=" ".join(df_dan.head(num1)["SO"].tolist()), height=150)
    with c2:
        num2 = st.number_input("Số quân Dàn 2 (Siêu phẩm):", 1, 100, 10)
        st.text_area("Dàn siêu phẩm:", value=" ".join(df_dan.head(num2)["SO"].tolist()), height=150)

    t_hist, t_c, t_b = st.tabs(["🕒 Lịch sử", "🗂️ Bảng C & D", "🎲 Bảng B"])
    with t_hist:
        st.subheader("Bảng Lịch sử & Thống kê Tỉ lệ Nổ")
        st.dataframe(pd.DataFrame(st.session_state.db["history"]), use_container_width=True, hide_index=True)
    with t_c:
        st.table(df_c)
        st.dataframe(df_dan.set_index("SO").T, use_container_width=True)
    with t_b: st.dataframe(df_b, use_container_width=True)

    st.sidebar.download_button("💾 SAO LƯU", json.dumps(st.session_state.db), "data_gan_pro.json")
