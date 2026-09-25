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
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu",
                    "--disable-blink-features=AutomationControlled",
                    "--ignore-certificate-errors"
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="vi-VN",
                timezone_id="Asia/Ho_Chi_Minh",
                device_scale_factor=1
            )
            
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
            
            page = context.new_page()
            print("Đang truy cập trang chủ xoiche.live...")
            
            try:
                page.goto(URL, timeout=35000, wait_until="domcontentloaded")
            except Exception:
                pass
            
            page.wait_for_timeout(8000)
            
            # QUAN TRỌNG: Click vào giữa màn hình để tắt các lớp quảng cáo ẩn / popup đè trang
            try:
                page.mouse.click(500, 500)
                page.wait_for_timeout(2000)
            except Exception:
                pass
            
            # Cuộn trang để ép tải dữ liệu trận đấu
            try:
                page.evaluate("window.scrollBy(0, 800);")
                page.wait_for_timeout(3000)
            except Exception:
                pass
            
            links = []
            try:
                links = page.locator("a").evaluate_all("elements => elements.map(e => ({href: e.href, text: e.innerText}))")
            except Exception:
                pass
                
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
                if count >= 15:
                    break
                
                stream_url = None
                match_page = context.new_page()
                
                def on_request(request):
                    nonlocal stream_url
                    req_lower = request.url.lower()
                    if not stream_url and any(kw in req_lower for kw in ['.m3u8', 'master.m3u8', 'playlist.m3u8', 'index.m3u8']):
                        stream_url = request.url

                match_page.on("request", on_request)
                
                try:
                    match_page.goto(match_url, timeout=15000, wait_until="domcontentloaded")
                    match_page.wait_for_timeout(4000)
                    
                    # Click tiếp vào trang chi tiết trận đấu để kích hoạt nút play/start của video nếu bị quảng cáo che
                    try:
                        match_page.mouse.click(600, 400)
                        match_page.wait_for_timeout(3000)
                    except Exception:
                        pass
                    
                    if not stream_url:
                        video_src = match_page.evaluate("() => { const v = document.querySelector('video'); return v ? v.src : null; }")
                        if video_src and 'http' in video_src:
                            stream_url = video_src
                except Exception:
                    pass
                
                match_page.close()
                
                if stream_url:
                    stream_url = stream_url.encode().decode('unicode-escape') if '\\u' in stream_url else stream_url
                    clean_title = re.sub(r'[\n\r\t]+', ' ', title).strip().upper()
                    playlist.append(f'#EXTINF:-1 group-title="Bóng Đá Trực Tiếp", [LIVE] {clean_title}\n')
                    playlist.append(f'{stream_url}\n')
                    count += 1
                    print(f"-> Đã lấy thành công link trận: {clean_title}")
                    
            browser.close()
    except Exception as e:
        print(f"Lỗi tổng quan: {e}")

    if len(playlist) <= 1:
        playlist.append('#EXTINF:-1 group-title="Bóng Đá Trực Tiếp", [THÔNG BÁO] Đang chờ cập nhật trận đấu\n')
        playlist.append('https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8\n')

    with open("xoilac_live.m3u", "w", encoding="utf-8") as f:
        f.writelines(playlist)
    print("Đã cập nhật danh sách M3U thành công!")

if __name__ == "__main__":
    main()
