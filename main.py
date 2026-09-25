import re
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

URL = "https://xoiche.live/"

def main():
    match_dict = {}
    playlist = ["#EXTM3U\n"]
    
    vn_tz = timezone(timedelta(hours=7))
    now = datetime.now(vn_tz)
    
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
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="vi-VN"
            )
            
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
            page = context.new_page()
            
            try:
                page.goto(URL, timeout=35000, wait_until="domcontentloaded")
            except Exception:
                pass
            
            page.wait_for_timeout(8000)
            
            try:
                page.mouse.click(500, 500)
                page.wait_for_timeout(2000)
                page.evaluate("window.scrollBy(0, 800);")
                page.wait_for_timeout(3000)
            except Exception:
                pass
            
            links = []
            try:
                links = page.locator("a").evaluate_all("elements => elements.map(e => ({href: e.href, text: e.innerText}))")
            except Exception:
                pass
                
            for l in links:
                href = l['href']
                raw_text = l['text'].strip().upper().replace('\n', ' ')
                
                if href and href != URL and 'xoiche.live' in href:
                    lower_href = href.lower()
                    if not any(x in lower_href for x in ['tin-tuc', 'kien-thuc', 'lien-he', 'sitemap', 'telegram', 'login', 'register']):
                        
                        # 1. TÌM VÀ ĐỊNH DẠNG SỐ PHÚT
                        minute = ""
                        min_match = re.search(r"(\d{1,3}\s*')", raw_text)
                        if min_match:
                            minute = min_match.group(1).replace(' ', '')
                        elif "HT" in raw_text or "NGHỈ GIỮA HIỆP" in raw_text:
                            minute = "HT"
                        elif "FT" in raw_text or "HẾT GIỜ" in raw_text:
                            minute = "FT"
                            
                        # Nếu không có dấu hiệu đang diễn ra thì bỏ qua
                        if not minute and not re.search(r'\d+\s*-\s*\d+', raw_text) and " VS " not in raw_text:
                            time_match = re.search(r'(\d{1,2}):(\d{2})', raw_text)
                            if time_match:
                                continue # Bỏ qua các trận tương lai chỉ có giờ
                            
                        # Danh sách từ rác cần dọn dẹp
                        trash_words = [
                            r'\[LIVE\]', r'LIVE', r'TRỰC TIẾP', r'BÓNG ĐÁ', r'NGHỈ GIỮA HIỆP', r'HT', r'FT', r'HẾT GIỜ',
                            r'UEFA EUROPA LEAGUE', r'UEFA CHAMPIONS LEAGUE', r'CHAMPIONS LEAGUE', r'EUROPA LEAGUE',
                            r'PREMIER LEAGUE', r'NGOẠI HẠNG ANH', r'LA LIGA', r'SERIE A', r'LIGUE 1', r'BUNDESLIGA',
                            r'VÒNG LOẠI', r'GIAO HỮU', r'CÚP QUỐC GIA', r'CÚP C1', r'CÚP C2', r'CÚP C3'
                        ]
                        
                        # 2. TÌM TỈ SỐ VÀ CHIA ĐỘI (Đội A Tỉ số : Tỉ số Đội B)
                        score_match = re.search(r'(\d+)\s*-\s*(\d+)', raw_text)
                        if score_match:
                            score_a = score_match.group(1)
                            score_b = score_match.group(2)
                            
                            # Cắt đôi chuỗi dựa vào tỉ số
                            parts = re.split(r'\d+\s*-\s*\d+', raw_text, maxsplit=1)
                            
                            # Xử lý phần Đội A (trước tỉ số)
                            a_clean = parts[0]
                            a_clean = re.sub(r'\d{1,2}:\d{2}', '', a_clean)
                            a_clean = re.sub(r'\d{1,2}[-/]\d{1,2}([-/]\d{2,4})?', '', a_clean)
                            for word in trash_words:
                                a_clean = re.sub(word, '', a_clean, flags=re.IGNORECASE)
                            if ':' in a_clean:
                                a_clean = a_clean.split(':')[-1]
                            a_clean = re.sub(r'[-|\[\]]', '', a_clean)
                            a_clean = re.sub(r'\s+', ' ', a_clean).strip()
                            
                            # Xử lý phần Đội B (sau tỉ số)
                            b_clean = parts[1]
                            b_clean = re.sub(r"\d{1,3}'", '', b_clean)
                            b_clean = re.sub(r'BLV\s+.*', '', b_clean, flags=re.IGNORECASE)
                            for word in trash_words:
                                b_clean = re.sub(word, '', b_clean, flags=re.IGNORECASE)
                            b_clean = re.sub(r'[-|\[\]]', '', b_clean)
                            b_clean = re.sub(r'\s+', ' ', b_clean).strip()
                            
                            clean_name = f"{a_clean} {score_a} : {score_b} {b_clean}"
                            if minute:
                                clean_name += f" | {minute}"
                        else:
                            # Không tìm thấy tỉ số (VD: chưa ghi bàn)
                            clean_name = raw_text
                            clean_name = re.sub(r'\d{1,2}:\d{2}', '', clean_name)
                            clean_name = re.sub(r'\d{1,2}[-/]\d{1,2}([-/]\d{2,4})?', '', clean_name)
                            clean_name = re.sub(r"\d{1,3}'", '', clean_name)
                            clean_name = re.sub(r'BLV\s+.*', '', clean_name, flags=re.IGNORECASE)
                            for word in trash_words:
                                clean_name = re.sub(word, '', clean_name, flags=re.IGNORECASE)
                            clean_name = re.sub(r'[-|\[\]]', '', clean_name)
                            clean_name = re.sub(r'\s+', ' ', clean_name).strip()
                            
                            if minute:
                                clean_name += f" | {minute}"
                                
                        if clean_name.replace(' | HT', '').replace(' | FT', '').strip() and href not in match_dict:
                            match_dict[href] = clean_name
            
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
                    playlist.append(f'#EXTINF:-1 group-title="Bóng Đá", {title}\n')
                    playlist.append(f'{stream_url}\n')
                    count += 1
                    
            browser.close()
    except Exception:
        pass

    if len(playlist) <= 1:
        playlist.append('#EXTINF:-1 group-title="Bóng Đá", Hiện chưa có trận đấu nào đang diễn ra\n')
        playlist.append('https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8\n')

    with open("xoilac_live.m3u", "w", encoding="utf-8") as f:
        f.writelines(playlist)

if __name__ == "__main__":
    main()
