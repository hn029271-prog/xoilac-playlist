import os
import re
import json
import requests
from bs4 import BeautifulSoup

# Danh sách miền dự phòng của Xoilac nếu xoiche1.live bị chặn
DOMAINS = [
    "https://xoiche1.live",
    "https://xoilac.live",
    "https://xoilac.tv",
    "https://xoilac.net"
]

M3U_FILE = "xoilac_live.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Referer": "https://xoiche1.live/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
}

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_matches_from_domain(domain):
    matches = []
    seen_urls = set()
    
    print(f"Đang thử kết nối tới: {domain}...")
    try:
        res = requests.get(domain, headers=HEADERS, timeout=12)
        res.encoding = 'utf-8'
        
        if res.status_code != 200:
            print(f"-> Không thể truy cập {domain} (Mã lỗi: {res.status_code})")
            return matches

        html_content = res.text
        soup = BeautifulSoup(html_content, 'html.parser')

        # Cách 1: Quét tất cả các thẻ <a> chứa đuôi trực tiếp
        links = soup.find_all('a', href=True)
        for a in links:
            href = a['href']
            # Tìm link có cấu trúc xem trực tiếp
            if any(path in href for path in ['/truc-tiep/', '/match/', '/xem-truc-tiep/', '/room/']):
                full_url = href if href.startswith("http") else f"{domain.rstrip('/')}/{href.lstrip('/')}"
                
                if full_url in seen_urls:
                    continue
                    
                # Lấy tên trận từ text hoặc attribute title/alt
                title = clean_text(a.get_text()) or clean_text(a.get('title', ''))
                
                # Bỏ qua các đường dẫn tin tức/highlight
                if not title or any(k in title.lower() for k in ['highlight', 'tin tức', 'lịch thi đấu', 'bảng xếp hạng']):
                    continue
                
                seen_urls.add(full_url)
                matches.append((title, full_url))

        # Cách 2: Nếu thẻ <a> bị ẩn, dùng Regex bắt trực tiếp đường dẫn từ JSON/Script nhúng trong HTML
        if not matches:
            print("-> Không tìm thấy thẻ <a> chuẩn, chuyển sang quét bằng Regex...")
            pattern = r'href=["\'](/truc-tiep/[^"\']+)["\']'
            found_paths = re.findall(pattern, html_content)
            
            for path in found_paths:
                full_url = f"{domain.rstrip('/')}/{path.lstrip('/')}"
                if full_url not in seen_urls:
                    # Trích xuất tên trận từ slug đường dẫn
                    slug_name = path.split('/')[-1].replace('-', ' ').title()
                    seen_urls.add(full_url)
                    matches.append((slug_name, full_url))

    except Exception as e:
        print(f"-> Lỗi khi xử lý {domain}: {e}")

    return matches

def main():
    all_matches = []
    
    # Thử lần lượt từng tên miền dự phòng cho đến khi cào được trận
    for domain in DOMAINS:
        all_matches = get_matches_from_domain(domain)
        if all_matches:
            print(f"==> Thành công! Quét được {len(all_matches)} trận đấu từ {domain}.")
            break

    # Ghi dữ liệu ra tệp .m3u
    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        
        if not all_matches:
            print("❌ Không quét được trận nào từ tất cả các nguồn.")
            f.write('#EXTINF:-1 tvg-logo="" group-title="Bóng Đá", [LIVE] Không tìm thấy trận đấu nào\n')
            f.write("https://example.com/live.m3u8\n")
        else:
            for title, url in all_matches:
                # Chuẩn hóa tên trận hiển thị đẹp trên máy TrimUI
                display_title = title if title.startswith("[LIVE]") else f"[LIVE] {title}"
                f.write(f'#EXTINF:-1 tvg-logo="" group-title="Bóng Đá", {display_title}\n')
                f.write(f'{url}\n')

if __name__ == "__main__":
    main()
