import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

BASE_TV_URL = "https://xoiche.tv"
M3U_FILE = "xoilac_live.m3u"

BACKUP_DOMAINS = [
    "https://xoiche1.live",
    "https://xoilac.live",
    "https://xoilac.tv"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Referer": "https://xoiche.tv/",
    "Accept": "*/*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
}

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def format_match_title(raw_text):
    """
    Xóa phần ngày giờ '23:00 | 28-09'
    Định dạng hiển thị: Tên Giải Đấu + Đội A Tỉ số Đội B | Phút'
    """
    text = clean_text(raw_text)
    
    # 1. Loại bỏ hoàn toàn định dạng giờ/ngày (VD: 23:00 | 28-09 hoặc 28-09-2026)
    text = re.sub(r'\d{1,2}:\d{2}\s*\|\s*\d{1,2}-\d{1,2}(-\d{2,4})?', '', text)
    text = re.sub(r'\d{1,2}:\d{2}', '', text)
    text = clean_text(text)

    # 2. Tìm phút thi đấu (VD: 73', 86', H1, H2, HT)
    minute_match = re.search(r"(\d+['′]|Hiệp \d|H\d|HT)", text, re.IGNORECASE)
    minute_str = ""
    if minute_match:
        minute_str = minute_match.group(1)
        # Xóa phút ra khỏi chuỗi thô để dễ xử lý tên giải/đội
        text = text.replace(minute_str, '').strip()

    # Nếu không có phút hoặc không có từ khóa đang đá -> Bỏ qua trận chưa đá
    if not minute_str and not any(k in text.lower() for k in ["live", "đang đá", "trực tiếp"]):
        return None

    if not minute_str:
        minute_str = "LIVE"

    # Xóa các từ thừa
    text = re.sub(r'^(Trực tiếp|Live|Xem|TRỰC TIẾP)\s+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+(blv|BLV).*$', '', text, flags=re.IGNORECASE) # Xóa tên BLV ở cuối

    # Ghép lại định dạng chuẩn đẹp
    formatted_title = f"{text} | {minute_str}"
    return formatted_title

def extract_direct_m3u8(match_url, domain):
    """
    Đi sâu vào trang trận đấu để lấy link .m3u8 chuẩn
    """
    try:
        headers = HEADERS.copy()
        headers["Referer"] = domain + "/"
        res = requests.get(match_url, headers=headers, timeout=8)
        
        if res.status_code == 200:
            html = res.text
            
            # 1. Tìm trực tiếp file .m3u8 trong HTML/JS
            m3u8_links = re.findall(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
            if m3u8_links:
                # Lọc bỏ link quảng cáo
                clean_links = [m for m in m3u8_links if not any(x in m.lower() for x in ['ad', 'promo', 'banner'])]
                if clean_links:
                    return clean_links[0]

            # 2. Bóc tách qua API ID của trận đấu
            match_id_search = re.search(r'/(?:room|match|truc-tiep)/([a-zA-Z0-9\-_]+)', match_url)
            if match_id_search:
                match_id = match_id_search.group(1)
                api_url = f"{domain}/api/v1/room/detail?id={match_id}"
                try:
                    api_res = requests.get(api_url, headers=headers, timeout=5)
                    if api_res.status_code == 200:
                        found = re.findall(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', api_res.text)
                        if found:
                            return found[0]
                except:
                    pass

            # 3. Quét Iframe Embed Player
            soup = BeautifulSoup(html, 'html.parser')
            for iframe in soup.find_all('iframe', src=True):
                src = iframe['src']
                if 'http' in src:
                    iframe_res = requests.get(src, headers=headers, timeout=5)
                    if iframe_res.status_code == 200:
                        found = re.findall(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', iframe_res.text)
                        if found:
                            return found[0]
    except Exception as e:
        print(f"Lỗi extract m3u8 từ {match_url}: {e}")
        
    return match_url

def get_live_matches(domain):
    matches = []
    seen_urls = set()
    
    print(f"Đang bóc tách danh sách từ: {domain}...")
    try:
        headers = HEADERS.copy()
        headers["Referer"] = domain + "/"
        
        res = requests.get(domain, headers=headers, timeout=10)
        res.encoding = 'utf-8'
        
        if res.status_code != 200:
            return matches

        soup = BeautifulSoup(res.text, 'html.parser')
        links = soup.find_all('a', href=True)
        
        for a in links:
            href = a['href']
            if any(path in href for path in ['/truc-tiep/', '/match/', '/xem-truc-tiep/', '/room/']):
                full_url = href if href.startswith("http") else f"{domain.rstrip('/')}/{href.lstrip('/')}"
                
                # Bỏ qua trùng lặp link BLV khác nhau của cùng 1 trận
                base_match_url = re.sub(r'\?blv=.*$', '', full_url)
                if base_match_url in seen_urls:
                    continue
                    
                raw_text = a.get_text(separator=" ") or a.get('title', '')
                title = format_match_title(raw_text)
                
                if title:
                    seen_urls.add(base_match_url)
                    print(f"-> Đang xử lý: {title}")
                    
                    # Tìm link .m3u8 phát trực tiếp
                    m3u8_url = extract_direct_m3u8(full_url, domain)
                    matches.append((title, m3u8_url))
                    
    except Exception as e:
        print(f"Lỗi cào dữ liệu từ {domain}: {e}")

    return matches

def main():
    live_matches = []
    
    for domain in BACKUP_DOMAINS:
        live_matches = get_live_matches(domain)
        if live_matches:
            break

    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        
        if not live_matches:
            print("Hiện tại không có trận đấu nào đang LIVE.")
            f.write('#EXTINF:-1 tvg-logo="" group-title="Bóng Đá", [LIVE] Hiện không có trận đấu nào đang đá\n')
            f.write("https://example.com/live.m3u8\n")
        else:
            print(f"==> Thành công ghi nhận {len(live_matches)} trận đấu.")
            for title, stream_url in live_matches:
                f.write(f'#EXTINF:-1 tvg-logo="" group-title="Bóng Đá", {title}\n')
                f.write(f'{stream_url}\n')

if __name__ == "__main__":
    main()
