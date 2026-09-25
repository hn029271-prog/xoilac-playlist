import re
from playwright.sync_api import sync_playwright

URL = "https://xoiche.live/"

def process_match_title(raw_text):
    text = raw_text.upper().replace('\n', ' ')

    # 1. Bỏ ngay các trận chưa đá / lịch tương lai
    if any(w in text for w in ["SẮP DIỄN RA", "HÔM NAY", "LỊCH THI ĐẤU"]):
        return None

    # 2. Lấy số phút thi đấu trước (VD: 86', 45+2', HT, FT)
    minute = ""
    min_match = re.search(r"(\d{1,3}(?:\+\d+)?\s*')", text)
    if min_match:
        minute = min_match.group(1).replace(' ', '')
        text = text.replace(min_match.group(0), ' ')
    elif "HT" in text or "NGHỈ GIỮA HIỆP" in text:
        minute = "HT"
    elif "FT" in text or "HẾT GIỜ" in text:
        minute = "FT"
    elif "ĐANG ĐÁ" in text or "LIVE" in text:
        minute = "LIVE"

    # 3. TRIỆT TÁC: Xóa Ngày/Tháng (25-09, 25/09) & Giờ (23:00) TRƯỚC KHI TÌM TỈ SỐ!
    text = re.sub(r'\b\d{1,2}[-/.]\d{1,2}([-/.]\d{2,4})?\b', ' ', text)
    text = re.sub(r'\b\d{1,2}:\d{2}\b', ' ', text)

    # 4. Tìm tỉ số thực sự của trận đấu (VD: 2-1, 1-0, 0-0)
    score_match = re.search(r'(\d+)\s*[-:]\s*(\d+)', text)

    # Không có cả Tỉ số LẪN Phút = Trận chưa đá -> Bỏ luôn
    if not score_match and not minute:
        return None

    # 5. Danh sách từ rác cần dọn dẹp (Giải đấu, BLV, Trực tiếp...)
    trash_patterns = [
        r'\[LIVE\]', r'\bLIVE\b', r'TRỰC TIẾP', r'BÓNG ĐÁ', r'ĐANG ĐÁ', r'NGHỈ GIỮA HIỆP',
        r'\bHT\b', r'\bFT\b', r'HẾT GIỜ', r'SẮP DIỄN RA', r'HÔM NAY', r'VS',
        r'UEFA NATIONS LEAGUE', r'NATIONS LEAGUE', r'CHAMPIONS LEAGUE', r'EUROPA LEAGUE',
        r'PREMIER LEAGUE', r'NGOẠI HẠNG ANH', r'LA LIGA', r'SERIE A', r'LIGUE 1', r'BUNDESLIGA',
        r'VÒNG LOẠI', r'GIAO HỮU', r'CÚP QUỐC GIA', r'CÚP C1', r'CÚP C2', r'CÚP C3', r'VÒNG\s+\d+'
    ]

    if score_match:
        parts = re.split(r'\d+\s*[-:]\s*\d+', text, maxsplit=1)
        team_a_raw = parts[0]
        team_b_raw = parts[1]
        score_a = score_match.group(1)
        score_b = score_match.group(2)

        def clean_sub(s):
            s = re.sub(r'BLV\s+.*', ' ', s, flags=re.IGNORECASE)
            for tp in trash_patterns:
                s = re.sub(tp, ' ', s, flags=re.IGNORECASE)
            s = re.sub(r'[\|\[\]\(\)\-\:\']', ' ', s)
            s = re.sub(r'\s+', ' ', s).strip()
            return s

        team_a = clean_sub(team_a_raw)
        team_b = clean_sub(team_b_raw)

        if not team_a or not team_b:
            return None

        title = f"{team_a} {score_a}-{score_b} {team_b}"
    else:
        def clean_all(s):
            s = re.sub(r'BLV\s+.*', ' ', s, flags=re.IGNORECASE)
            for tp in trash_patterns:
                s = re.sub(tp, ' ', s, flags=re.IGNORECASE)
            s = re.sub(r'[\|\[\]\(\)\-\:\']', ' ', s)
            s = re.sub(r'\s+', ' ', s).strip()
            return s
        title = clean_all(text)

    # Gắn thêm phút trực tiếp nếu có
    if minute:
        title += f" | {minute}"

    return title

def main():
    match_dict = {}
    playlist = ["#EXTM3U\n"]
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas", "--disable-gpu"
                ]
            )
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
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
                raw_text = l['text'].strip()
                
                if href and href != URL and 'xoiche.live' in href:
                    if any(x in href.lower() for x in ['tin-tuc', 'kien-thuc', 'lien-he', 'telegram', 'login', 'register']):
                        continue
                        
                    clean_title = process_match_title(raw_text)
                    if clean_title and href not in match_dict:
                        match_dict[href] = clean_title
            
            count = 0
            for match_url, title in match_dict.items():
                if count >= 15:
                    break
                
                stream_url = None
                match_page = context.new_page()
                
                def on_request(request):
                    nonlocal stream_url
                    if not stream_url and any(kw in request.url.lower() for kw in ['.m3u8']):
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
