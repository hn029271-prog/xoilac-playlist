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
    "https://xoilac.tv",
    "https://xoilac.net"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Referer": "https://xoiche.tv/",
    "Accept": "*/*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
}

def get_latest_live_domain():
    print(f"Đang truy cập {BASE_TV_URL} để lấy domain LIVE mới nhất...")
    try:
        res = requests.get(BASE_TV_URL, headers=HEADERS, timeout=12)
        res.encoding = 'utf-8'
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            for a in links:
                href = a['href'].strip()
                text = (a.get_text() or "").lower()
                
                if any(social in href for social in ['t.me', 'telegram', 'facebook', 'zalo', 'youtube']):
                    continue
                
                if any(k in text for k in ['xem ngay', 'xem live']) or ('http' in href and 'xoiche.tv' not in href):
                    if href.startswith('http'):
                        parsed = urlparse(href)
                        live_domain = f"{parsed.scheme}://{parsed.netloc}"
                        print(f"==> Đã tìm thấy domain LIVE chuẩn: {live_domain}")
                        return live_domain
    except Exception as e:
        print(f"Lỗi khi tìm domain từ {BASE_TV_URL}: {e}")
        
    return None

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_match_title(raw_text):
    text = clean_text(raw_text)
    
    if any(k in text.lower() for k in ['highlight', 'tin tức', 'lịch thi đấu', 'bảng xếp hạng']):
        return None, False

    minute_match = re.search(r"(\d+['′]|Hiệp \d|H\d|HT)", text, re.IGNORECASE)
    
    is_live = False
    minute_str = ""
    
    if minute_match:
        is_live = True
        minute_str = minute_match.group(1)
    elif any(k in text.lower() for k in ["live", "đang đá", "trực tiếp"]):
        is_live = True
        minute_str = "LIVE"

    if not is_live:
        return None, False

    score_match = re.search(r"([A-Za-z0-9\sÀ-ỹ]+?)\s+(\d+\s*[-–]\s*\d+)\s+([A-Za-z0-9\sÀ-ỹ]+)", text)
    
    if score_match:
        team_a = clean_text(score_match.group(1))
        score = clean_text(score_match.group(2)).replace(" ", "")
        team_b = clean_text(score_match.group(3))
        
        team_a = re.sub(r'^(Trực tiếp|Live|Xem|TRỰC TIẾP)\s+', '', team_a, flags=re.IGNORECASE)
        team_b = re.sub(r'\s+(Trực tiếp|Live|Xem|TRỰC TIẾP)$', '', team_b, flags=re.IGNORECASE)
        
        formatted = f"{team_a} {score} {team_b} | {minute_str}"
        return formatted, True
    else:
        clean_title = re.sub(r'^(Trực tiếp|Live|Xem)\s+', '', text, flags=re.IGNORECASE)
        clean_title = re.sub(r'\s+(xem trực tiếp|link xem)$', '', clean_title, flags=re.IGNORECASE)
        
        if minute_str and minute_str not in clean_title:
            clean_title = f"{clean_title} | {minute_str}"
            
        return clean_title, True

def extract_direct_m3u8_url(match_page_url, domain):
    """
    Truy xuất luồng phát m3u8 thông qua HTML, Regex JS, Embed Iframe và API Endpoint.
    """
    try:
        headers = HEADERS.copy()
        headers["Referer"] = domain + "/"
        res = requests.get(match_page_url, headers=headers, timeout=10)
        
        if res.status_code == 200:
            html = res.text
            
            # 1. Tìm trực tiếp file .m3u8 hoặc luồng hls trong HTML/JS
            m3u8_matches = re.findall(r'(https?://[^\s"\']+\.(?:m3u8|flv)[^\s"\']*)', html)
            if m3u8_matches:
                clean_streams = [m for m in m3u8_matches if not any(x in m.lower() for x in ['ad', 'promo', 'banner'])]
                if clean_streams:
                    return clean_streams[0]

            # 2. Bóc tách ID trận đấu để gọi API lấy link stream trực tiếp
            match_id = None
            id_search = re.search(r'/(?:room|match|truc-tiep)/([a-zA-Z0-9\-_]+)', match_page_url)
            if id_search:
                match_id = id_search.group(1)
                
            if match_id:
                # Các endpoint API stream phổ biến của hệ thống Xoilac
                api_endpoints = [
                    f"{domain}/api/v1/room/detail?id={match_id}",
                    f"{domain}/api/match/{match_id}/stream",
                    f"{domain}/json/{match_id}.json"
                ]
                for api in api_endpoints:
                    try:
                        api_res = requests.get(api, headers=headers, timeout=5)
                        if api_res.status_code == 200 and 'm3u8' in api_res.text:
                            found = re.findall(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', api_res.text)
                            if found:
                                return found[0]
                    except:
                        pass

            # 3. Quét các iframe player nhúng
            soup = BeautifulSoup(html, 'html.parser')
            iframes = soup.find_all('iframe', src=True)
            for iframe in iframes:
                src = iframe['src']
                if 'http' in src and any(k in src for k in ['embed', 'player', 'stream', 'live', 'play']):
                    try:
                        iframe_headers = headers.copy()
                        iframe_headers["Referer"] = match_page_url
                        iframe_res = requests.get(src, headers=iframe_headers, timeout=6)
                        if iframe_res.status_code == 200:
                            inner_m3u8 = re.findall(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', iframe_res.text)
                            if inner_m3u8:
                                return inner_m3u8[0]
                    except:
                        pass
    except Exception as e:
        print(f"Không lấy được link stream từ {match_page_url}: {e}")
        
    return match_page_url

def get_live_matches(domain):
    matches = []
    seen_urls = set()
    
    print(f"Đang bóc tách danh sách trận đấu từ: {domain}...")
    try:
        headers = HEADERS.copy()
        headers["Referer"] = domain + "/"
        
        res = requests.get(domain, headers=headers, timeout=12)
        res.encoding = 'utf-8'
        
        if res.status_code != 200:
            return matches

        soup = BeautifulSoup(res.text, 'html.parser')
        links = soup.find_all('a', href=True)
        
        for a in links:
            href = a['href']
            if any(path in href for path in ['/truc-tiep/', '/match/', '/xem-truc-tiep/', '/room/']):
                full_url = href if href.startswith("http") else f"{domain.rstrip('/')}/{href.lstrip('/')}"
                
                if full_url in seen_urls:
                    continue
                    
                raw_text = a.get_text(separator=" ") or a.get('title', '')
                title, is_live = parse_match_title(raw_text)
                
                if is_live and title:
                    seen_urls.add(full_url)
                    print(f"-> Phát hiện trận LIVE: {title}")
                    
                    m3u8_stream = extract_direct_m3u8_url(full_url, domain)
                    matches.append((title, m3u8_stream))
                    
    except Exception as e:
        print(f"Lỗi khi cào dữ liệu từ {domain}: {e}")

    return matches

def main():
    live_matches = []
    
    live_domain = get_latest_live_domain()
    if live_domain:
        live_matches = get_live_matches(live_domain)

    if not live_matches:
        for backup in BACKUP_DOMAINS:
            live_matches = get_live_matches(backup)
            if live_matches:
                break

    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        
        if not live_matches:
            print("Hiện tại không có trận đấu nào đang LIVE.")
            f.write('#EXTINF:-1 tvg-logo="" group-title="Bóng Đá", [LIVE] Hiện không có trận đấu nào đang đá\n')
            f.write("https://example.com/live.m3u8\n")
        else:
            print(f"==> Hoàn tất! Đã cập nhật {len(live_matches)} trận đấu.")
            for title, stream_url in live_matches:
                f.write(f'#EXTINF:-1 tvg-logo="" group-title="Bóng Đá", {title}\n')
                f.write(f'{stream_url}\n')

if __name__ == "__main__":
    main()
