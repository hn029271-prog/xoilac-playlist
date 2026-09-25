import re
from playwright.sync_api import sync_playwright

URL = "https://xoiche.live/"

def clean_team_name(text):
    # Quét sạch 100% các cụm ngày giờ bất chấp định dạng (25:09, 25/09, 25-09...)
    text = re.sub(r'\d{1,2}[:/\-]\d{1,2}([:/\-]\d{2,4})?', '', text)
    
    # Xóa các con số lạc lõng đứng đầu câu (phòng hờ ngày tháng bị vỡ)
    text = re.sub(r'^\s*\d+\s*', '', text)
    
    # Xóa các từ rác phổ biến và tên giải đấu
    trash_words = [
        'SẮP DIỄN RA', '[LIVE]', 'LIVE', 'TRỰC TIẾP', 'BÓNG ĐÁ', 'ĐANG ĐÁ', 'NGHỈ GIỮA HIỆP', 'HT', 'FT', 'HẾT GIỜ', 'VS',
        'UEFA NATIONS LEAGUE', 'NATIONS LEAGUE', 'CHAMPIONS LEAGUE', 'EUROPA LEAGUE', 'PREMIER LEAGUE',
        'NGOẠI HẠNG ANH', 'LA LIGA', 'SERIE A', 'LIGUE 1', 'BUNDESLIGA', 'VÒNG LOẠI', 'GIAO HỮU', 'CÚP', 'VÒNG'
    ]
    for t in trash_words:
        text = re.sub(r'\b' + t + r'\b', '', text, flags=re.IGNORECASE)
        text = text.replace(f'[{t}]', '')
        
    # Xóa phần tên BLV trở về sau
    text = re.sub(r'BLV\s+.*', '', text)
    # Xóa phút thi đấu nếu còn sót
    text = re.sub(r"\d{1,3}'", '', text)
    # Dọn dẹp ký tự thừa (dấu gạch, ngoặc, hai chấm)
    text = re.sub(r'[\|\[\]\(\)\-\:]', ' ', text)
    # Xóa khoảng trắng thừa
    text = re.sub(r'\s+', ' ', text).strip()
    return text

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
                raw_text = l['text'].strip().upper().replace('\n', ' ')
                
                if href and href != URL and 'xoiche.live' in href:
                    if any(x in href.lower() for x in ['tin-tuc', 'kien-thuc', 'lien-he', 'telegram', 'login', 'register']):
                        continue
                        
                    if "SẮP DIỄN RA" in raw_text or "HÔM NAY" in raw_text:
                        continue

                    score_match = re.search(r'(\d+)\s*-\s*(\d+)', raw_text)
                    min_match = re.search(r"(\d{1,3}\s*')", raw_text)
                    
                    minute = ""
                    if min_match:
                        minute = min_match.group(1).replace(' ', '')
                    elif "HT" in raw_text or "NGHỈ GIỮA HIỆP" in raw_text:
                        minute = "HT"
                    elif "FT" in raw_text or "HẾT GIỜ" in raw_text:
                        minute = "FT"
                    elif "ĐANG ĐÁ" in raw_text:
                        minute = "LIVE"

                    if not score_match and not minute:
                        continue
                        
                    if score_match:
                        parts = re.split(r'\d+\s*-\s*\d+', raw_text, maxsplit=1)
                        team_a = clean_team_name(parts[0])
                        team_b = clean_team_name(parts[1])
                        score_a = score_match.group(1)
                        score_b = score_match.group(2)
                        
                        # Đổi dấu ":" thành "-" để tránh lỗi ẩn ký tự trên app RomCloud
                        final_name = f"{team_a} {score_a} - {score_b} {team_b}"
                    else:
                        final_name = clean_team_name(raw_text)

                    if minute:
                        final_name += f" | {minute}"
                        
                    if final_name.replace(f" | {minute}", "").strip() and href not in match_dict:
                        match_dict[href] = final_name.strip()
            
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
