import os
import re
import requests
from bs4 import BeautifulSoup

# Cập nhật tên miền mới
DOMAIN = "https://xoiche1.live"
M3U_FILE = "xoilac_live.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": f"{DOMAIN}/",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
}

def fetch_xoilac_matches():
    matches = []
    try:
        res = requests.get(DOMAIN, headers=HEADERS, timeout=12)
        res.encoding = 'utf-8'
        if res.status_code != 200:
            print(f"Lỗi truy cập {DOMAIN}: HTTP {res.status_code}")
            return matches

        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Thẻ chứa danh sách trận đấu trên hệ thống Xoilac/Xoiche mới
        items = soup.select('a[href*="/truc-tiep/"], a[href*="/match/"], a[href*="/room/"]')
        
        seen_urls = set()
        for item in items:
            href = item.get('href', '')
            if not href:
                continue
                
            full_url = href if href.startswith("http") else f"{DOMAIN}{href}"
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            
            # Lấy tiêu đề trận đấu, tỉ số, số phút & BLV
            raw_text = item.get_text(separator=" ", strip=True)
            clean_title = re.sub(r'\s+', ' ', raw_text)
            
            # Chỉ lấy các mục có nội dung trận đấu thực sự (loại bỏ bài viết, tin tức)
            if len(clean_title) > 5 and not any(x in clean_title.lower() for x in ["highlight", "tin tức", "lịch thi đấu", "bảng xếp hạng"]):
                # Tự động gán nhãn [LIVE] cho các trận cào được
                if "[LIVE]" not in clean_title.upper():
                    clean_title = f"[LIVE] {clean_title}"
                matches.append((clean_title, full_url))
                
    except Exception as e:
        print(f"Lỗi trong quá trình quét dữ liệu: {e}")
        
    return matches

def save_to_m3u(matches):
    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        if not matches:
            f.write('#EXTINF:-1 tvg-logo="" group-title="Bóng Đá", [LIVE] Hiện chưa có trận đấu nào\n')
            f.write("https://example.com/live.m3u8\n")
            print("Không tìm thấy trận đấu nào, đã tạo file m3u rỗng tạm thời.")
            return

        for idx, (title, url) in enumerate(matches, 1):
            f.write(f'#EXTINF:-1 tvg-logo="" group-title="Bóng Đá", {title}\n')
            f.write(f'{url}\n')
            
    print(f"Đã xuất thành công {len(matches)} trận đấu vào {M3U_FILE}")

if __name__ == "__main__":
    print(f"Bắt đầu quét dữ liệu bóng đá từ {DOMAIN}...")
    live_matches = fetch_xoilac_matches()
    save_to_m3u(live_matches)
