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

def main():
    match_dict = {}
    playlist = ["#EXTM3U\n"]
    
    with sync_playwright() as p:
        # Khởi chạy trình duyệt ngầm
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=headers["User-Agent"])
        
        # 1. Quét trang chủ bằng Playwright để lấy danh sách trận đấu động
        page = context.new_page()
        try:
            print("Đang truy cập trang chủ...")
            page.goto(URL, timeout=20000)
            page.wait_for_timeout(5000) # Chờ trang load xong dữ liệu JavaScript
            
            # Lấy tất cả các thẻ a trên trang chủ
            links = page.locator("a").evaluate_all("elements => elements.map(e => ({href: e.href, text: e.innerText}))")
            for l in links:
                href = l['href']
                if '/tran-dau/' in href or '/match/' in href:
                    title = l['text'].strip()
                    if not title or len(title) < 3:
                        title = href.split('/')[-1].replace('-', ' ')
                    cleaned = clean_match_name(title)
                    if cleaned and href not in match_dict:
                        match_dict[href] = cleaned
        except Exception as e:
            print(f"Lỗi quét trang chủ: {e}")
        page.close()
        
        print(f"Tìm thấy {len(match_dict)} trận đấu.")
        
        # 2. Vào từng trang trận đấu để bắt link .m3u8 thực tế kèm token
        count = 0
        for match_url, title in match_dict.items():
            if count >= 6:  # Lấy tối đa 6 trận để chạy mượt
                break
            
            stream_url = None
            match_page = context.new_page()
            
            def on_request(request):
                nonlocal stream_url
                if '.m3u8' in request.url and not stream_url:
                    stream_url = request.url

            match_page.on("request", on_request)
            
            try:
                match_page.goto(match_url, timeout=15000)
                match_page.wait_for_timeout(4000) # Chờ player kích hoạt stream
            except Exception:
                pass
            
            match_page.close()
            
            if stream_url:
                stream_url = stream_url.encode().decode('unicode-escape') if '\\u' in stream_url else stream_url
                playlist.append(f'#EXTINF:-1 group-title="Bóng Đá Trực Tiếp", [LIVE] {title}\n')
                playlist.append(f'{stream_url}\n')
                count += 1
                
        browser.close()

    # Nếu vẫn không bắt được trận nào, hiển thị thông báo chờ
    if len(playlist) <= 1:
        playlist.append('#EXTINF:-1 group-title="Bóng Đá Trực Tiếp", [THÔNG BÁO] Đang chờ trận đấu trực tiếp\n')
        playlist.append('https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8\n')

    with open("xoilac_live.m3u", "w", encoding="utf-8") as f:
        f.writelines(playlist)
    print("Đã cập nhật danh sách M3U thành công!")

if __name__ == "__main__":
    main()
