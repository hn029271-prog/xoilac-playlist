from playwright.sync_api import sync_playwright
import re

URL = "https://xoiche.tv/"

def clean_match_name(raw_title):
    if not raw_title:
        return None
    title = re.sub(r'\s+(?:kg|id)?\s*\d+', '', raw_title, flags=re.IGNORECASE)
    title = re.sub(r'[\?#].*', '', title)
    title = title.strip().upper()
    if len(title) < 3:
        return None
    return title

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
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            
            page = context.new_page()
            print("Đang truy cập trang chủ...")
            page.goto(URL, timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            
            links = page.locator("a").evaluate_all("elements => elements.map(e => ({href: e.href, text: e.innerText}))")
            print(f"DEBUG - Tổng số link tìm thấy trên trang: {len(links)}")
            
            for i, l in enumerate(links[:20]):
                print(f"Mẫu {i+1}: href='{l['href']}' | text='{l['text'].strip()}'")
            
            for l in links:
                href = l['href']
                if href and href != URL:
                    title = l['text'].strip()
                    if not title or len(title) < 3:
                        title = href.split('/')[-1].replace('-', ' ')
                    cleaned = clean_match_name(title)
                    if cleaned and href not in match_dict:
                        match_dict[href] = cleaned
            
            print(f"Lọc được {len(match_dict)} trận đấu hợp lệ.")
            
            count = 0
            for match_url, title in match_dict.items():
                if count >= 6:
                    break
                
                stream_url = None
                match_page = context.new_page()
                
                def on_request(request):
                    nonlocal stream_url
                    if '.m3u8' in request.url and not stream_url:
                        stream_url = request.url

                match_page.on("request", on_request)
                
                try:
                    match_page.goto(match_url, timeout=15000, wait_until="domcontentloaded")
                    match_page.wait_for_timeout(3000)
                except Exception:
                    pass
                
                match_page.close()
                
                if stream_url:
                    stream_url = stream_url.encode().decode('unicode-escape') if '\\u' in stream_url else stream_url
                    playlist.append(f'#EXTINF:-1 group-title="Bóng Đá Trực Tiếp", [LIVE] {title}\n')
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
