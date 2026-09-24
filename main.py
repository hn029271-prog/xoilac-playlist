import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import re

URL = "https://xoiche.tv/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_match_name(raw_title):
    if not raw_title:
        return None
    lower_title = raw_title.lower()
    if any(keyword in lower_title for keyword in ["nhà đài", "blv", "kênh", "soi kèo", "lịch thi đấu"]):
        return None
    title = re.sub(r'\s+(?:kg|id)?\s*\d+', '', raw_title, flags=re.IGNORECASE)
    title = re.sub(r'[\?#].*', '', title)
    title = title.strip().upper()
    if len(title) < 4:
        return None
    return title

def get_matches_from_homepage():
    try:
        resp = requests.get(URL, headers=headers, timeout=10)
        if resp.status_code != 200:
            return {}
        soup = BeautifulSoup(resp.text, 'html.parser')
        links = soup.find_all('a', href=True)
        match_dict = {}
        for l in links:
            href = l['href']
            if '/tran-dau/' in href or '/match/' in href:
                match_url = "https://xoiche.tv" + href if not href.startswith('http') else href
                title = l.get_text(strip=True)
                if not title or len(title) < 3:
                    title = href.split('/')[-1].replace('-', ' ')
                cleaned = clean_match_name(title)
                if cleaned:
                    match_dict[match_url] = cleaned
        return match_dict
    except Exception as e:
        print(f"Lỗi quét trang chủ: {e}")
        return {}

def main():
    match_dict = get_matches_from_homepage()
    playlist = ["#EXTM3U\n"]
    
    if match_dict:
        with sync_playwright() as p:
            # Khởi chạy trình duyệt ẩn danh (giống hệt môi trường bạn dùng F12)
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=headers["User-Agent"])
            
            count = 0
            for match_url, title in match_dict.items():
                if count >= 6:  # Lấy tối đa 6 trận để tối ưu tốc độ chạy ngầm
                    break
                
                stream_url = None
                page = context.new_page()
                
                # Bắt sự kiện Network request chứa .m3u8 (như tab Network ở F12)
                def on_request(request):
                    nonlocal stream_url
                    if '.m3u8' in request.url and not stream_url:
                        stream_url = request.url

                page.on("request", on_request)
                
                try:
                    page.goto(match_url, timeout=15000)
                    # Chờ 4 giây để trình duyệt chạy player và kích hoạt request lấy link stream thật
                    page.wait_for_timeout(4000)
                except Exception:
                    pass
                
                page.close()
                
                if stream_url:
                    stream_url = stream_url.encode().decode('unicode-escape') if '\\u' in stream_url else stream_url
                    playlist.append(f'#EXTINF:-1 group-title="Bóng Đá Trực Tiếp", [LIVE] {title}\n')
                    playlist.append(f'{stream_url}\n')
                    count += 1
                    
            browser.close()

    # Nếu không bắt được link nào, giữ lại thông báo để file không bị lỗi trống
    if len(playlist) <= 1:
        playlist.append('#EXTINF:-1 group-title="Bóng Đá Trực Tiếp", [THÔNG BÁO] Đang chờ trận đấu trực tiếp\n')
        playlist.append('https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8\n')

    with open("xoilac_live.m3u", "w", encoding="utf-8") as f:
        f.writelines(playlist)
    print("Đã cập nhật M3U với token thực tế thành công!")

if __name__ == "__main__":
    main()
