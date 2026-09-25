from playwright.sync_api import sync_playwright
import re

URL = "https://xoiche.live/"

def main():
    match_dict = {}
    playlist = ["#EXTM3U\n"]
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            
            page = context.new_page()
            print("Đang truy cập trang chủ xoiche.live...")
            
            try:
                page.goto(URL, timeout=30000, wait_until="domcontentloaded")
            except Exception:
                pass
            
            # Đợi đủ 9 giây để JavaScript của trang kịp render danh sách trận đấu ra HTML
            print("Đang chờ trang hiển thị đầy đủ danh sách trận đấu...")
            page.wait_for_timeout(9000)
            
            # Cuộn trang an toàn xuống dưới để ép trang tải các trận phía dưới
            for _ in range(3):
                try:
                    page.evaluate("window.scrollBy(0, 1000);")
                    page.wait_for_timeout(2000)
                except Exception:
                    pass
            
            links = page.locator("a").evaluate_all("elements => elements.map(e => ({href: e.href, text: e.innerText}))")
            print(f"DEBUG - Tổng số link tìm thấy: {len(links)}")
            
            for l in links:
                href = l['href']
                text = l['text'].strip()
                if href and href != URL and 'xoiche.live' in href:
                    lower_href = href.lower()
                    if not any(x in lower_href for x in ['tin-tuc', 'kien-thuc', 'lien-he', 'sitemap', 'telegram', 't.me', 'login', 'register', 'highlight']):
                        match_title = text if len(text) > 3 else href.split('/')[-1].replace('-', ' ').upper()
                        if href not in match_dict:
                            match_dict[href] = match_title
            
            print(f"Lọc được tổng cộng {len(match_dict)} trận đấu tiềm năng.")
            
            count = 0
            for match_url, title in match_dict.items():
                if count >= 15: # Lấy tối đa 15 trận
                    break
                
                stream_url = None
                match_page = context.new_page()
                
                def on_request(request):
                    nonlocal stream_url
                    if '.m3u8' in request.url and not stream_url:
                        stream_url = request.url

                match_page.on("request", on_request)
                
                try:
                    match_page.goto(match_url, timeout=10000, wait_until="domcontentloaded")
                    match_page.wait_for_timeout(3000)
                except Exception:
                    pass
                
                match_page.close()
                
                if stream_url:
                    stream_url = stream_url.encode().decode('unicode-escape') if '\\u' in stream_url else stream_url
                    clean_title = re.sub(r'[\n\r\t]+', ' ', title).strip().upper()
                    playlist.append(f'#EXTINF:-1 group-title="Bóng Đá Trực Tiếp", [LIVE] {clean_title}\n')
                    playlist.append(f'{stream_url}\n')
                    count += 1
                    
            browser.close()
    except Exception as e:
        print(f"Lỗi tổng quan: {e}")

    if len(playlist) <= 1:
        playlist.append('#EXTINF:-1 group-title="Bóng Đá Trực Tiếp", [THÔNG BÁO] Đang chờ trận đấu trực tiếp\n')
        playlist.append('https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8\n')

    with open("xoilac_live.m3u", "w", encoding="utf-8") as f:
        f.writelines(playlist)
    print("Đã cập nhật danh sách M3U thành công!")

if __name__ == "__main__":
    main()
