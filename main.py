import os
import re
import requests

M3U_FILE = "xoilac_live.m3u"

# Các cổng API lấy thông tin stream của hệ thống Xoilac/Xoiche
API_ENDPOINTS = [
    "https://api.xoilac.live/api/room/list",
    "https://api.xoiche.tv/api/v1/matches/live",
    "https://xoiche1.live/api/v1/room/list"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Origin": "https://xoiche1.live",
    "Referer": "https://xoiche1.live/",
    "Accept": "application/json, text/plain, */*"
}

def clean_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', str(text)).strip()

def extract_m3u8_from_page(match_url):
    """
    Truy cập trang trận đấu, quét các thẻ script JSON-LD hoặc biến JavaScript
    chứa đường dẫn .m3u8
    """
    try:
        res = requests.get(match_url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            html = res.text
            
            # Tìm link .m3u8 trong JavaScript
            m3u8_matches = re.findall(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
            if m3u8_matches:
                # Lọc bỏ các đường dẫn quảng cáo (ad, promo)
                clean_links = [m for m in m3u8_matches if not any(x in m.lower() for x in ['ad', 'promo', 'banner'])]
                if clean_links:
                    return clean_links[0]
                return m3u8_matches[0]
                
            # Tìm đường dẫn hls/stream mã hóa trong player config
            stream_matches = re.findall(r'["\'](https?://[^\s"\']+(?:hls|stream|live)[^\s"\']*)["\']', html)
            if stream_matches:
                return stream_matches[0]
    except Exception as e:
        print(f"Lỗi khi cào m3u8 từ {match_url}: {e}")
    
    return None

def fetch_live_matches_via_api():
    matches = []
    
    # 1. Thử gọi các API endpoint nội bộ
    for api_url in API_ENDPOINTS:
        try:
            print(f"Đang kiểm tra API: {api_url}")
            res = requests.get(api_url, headers=HEADERS, timeout=8)
            if res.status_code == 200:
                data = res.json()
                items = data.get('data', []) if isinstance(data, dict) else data
                
                if isinstance(items, list) and len(items) > 0:
                    for match in items:
                        # Chỉ lấy trận đang LIVE
                        status = str(match.get('status', '')).lower()
                        is_live = match.get('is_live', False) or status in ['live', 'playing', '1']
                        
                        if is_live:
                            league = clean_text(match.get('league_name') or match.get('tournament', 'Bóng Đá'))
                            home = clean_text(match.get('home_name') or match.get('home_team', 'Đội A'))
                            away = clean_text(match.get('away_name') or match.get('away_team', 'Đội B'))
                            score_home = match.get('home_score', '0')
                            score_away = match.get('away_score', '0')
                            minute = match.get('minute') or match.get('match_time') or 'LIVE'
                            
                            title = f"{league} {home} {score_home} : {score_away} {away} | {minute}'"
                            
                            # Lấy link m3u8 trực tiếp từ JSON API
                            stream_url = match.get('hls') or match.get('m3u8') or match.get('stream_url')
                            if stream_url and '.m3u8' in stream_url:
                                matches.append((title, stream_url))
        except Exception as e:
            print(f"API {api_url} không phản hồi: {e}")

    return matches

def scrape_web_fallback():
    """
    Phương án dự phòng nếu API bị đổi: Quét HTML trang chủ và giải mã từng trang con
    """
    matches = []
    domain = "https://xoiche1.live"
    print(f"Đang quét giao diện web dự phòng: {domain}")
    
    try:
        from bs4 import BeautifulSoup
        res = requests.get(domain, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.find_all('a', href=True)
            seen_urls = set()
            
            for a in links:
                href = a['href']
                if '/truc-tiep/' in href:
                    full_url = href if href.startswith("http") else f"{domain.rstrip('/')}/{href.lstrip('/')}"
                    base_url = re.sub(r'\?blv=.*$', '', full_url)
                    
                    if base_url in seen_urls:
                        continue
                    seen_urls.add(base_url)
                    
                    raw_text = clean_text(a.get_text(separator=" "))
                    
                    # Lọc phút
                    min_match = re.search(r"(\d+['′])", raw_text)
                    if min_match:
                        minute = min_match.group(1)
                        # Làm sạch tên trận
                        clean_title = re.sub(r'\d{1,2}:\d{2}\s*\|\s*\d{1,2}-\d{1,2}(-\d{2,4})?', '', raw_text)
                        clean_title = re.sub(r'^(Trực tiếp|Live|Xem)\s+', '', clean_title, flags=re.IGNORECASE)
                        clean_title = re.sub(r'\s+blv.*$', '', clean_title, flags=re.IGNORECASE)
                        
                        title = f"{clean_title.strip()} | {minute}"
                        
                        # Giải mã ra link .m3u8 thật
                        m3u8_url = extract_m3u8_from_page(full_url)
                        if m3u8_url:
                            matches.append((title, m3u8_url))
    except Exception as e:
        print(f"Lỗi fallback web: {e}")
        
    return matches

def main():
    # 1. Thử cào qua API trước
    live_matches = fetch_live_matches_via_api()
    
    # 2. Nếu API không có dữ liệu, chuyển sang cào Web + Bóc m3u8 sâu
    if not live_matches:
        live_matches = scrape_web_fallback()

    # 3. Xuất file M3U
    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        
        if not live_matches:
            print("Hiện tại không có trận đấu nào đang LIVE.")
            f.write('#EXTINF:-1 tvg-logo="" group-title="Bóng Đá", [LIVE] Hiện không có trận đấu nào đang đá\n')
            f.write("https://example.com/live.m3u8\n")
        else:
            print(f"==> Đã bóc tách thành công {len(live_matches)} link stream .m3u8!")
            for title, stream_url in live_matches:
                f.write(f'#EXTINF:-1 tvg-logo="" group-title="Bóng Đá", {title}\n')
                f.write(f'{stream_url}\n')

if __name__ == "__main__":
    main()
