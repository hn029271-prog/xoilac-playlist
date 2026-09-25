import re
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

URL = "https://xoiche.live/"

def main():
    match_dict = {}
    playlist = ["#EXTM3U\n"]
    
    # Thiết lập múi giờ Việt Nam (UTC+7) để bộ đếm giờ hoạt động chuẩn xác
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
            
            try:
                page.mouse.click(500, 500)
                page.wait_for_timeout(2000)
            except Exception:
                pass
            
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
                raw_text = l['text'].strip().upper()
                
                if href and href != URL and 'xoiche.live' in href:
                    lower_href = href.lower()
                    if not any(x in lower_href for x in ['tin-tuc', 'kien-thuc', 'lien-he', 'sitemap', 'telegram', 't.me', 'login', 'register', 'highlight']):
                        
                        # ==========================================
                        # 1. BỘ LỌC THỜI GIAN: LOẠI BỎ TRẬN CHƯA ĐÁ
                        # ==========================================
                        time_match = re.search(r'(\d{1,2}):(\d{2})', raw_text)
                        date_match = re.search(r'(\d{1,2})[-/](\d{1,2})', raw_text)
                        
                        is_live = False
                        if time_match and date_match:
                            match_hour = int(time_match.group(1))
                            match_minute = int(time_match.group(2))
                            match_day = int(date_match.group(1))
                            match_month = int(date_match.group(2))
                            
                            try:
                                match_time = datetime(now.year, match_month, match_day, match_hour, match_minute, tzinfo=vn_tz)
                                
                                # Tính toán chênh lệch thời gian so với hiện tại (phút)
                                time_diff = (now - match_time).total_seconds() / 60
                                
                                # CHỈ LẤY: Các trận bắt đầu trước đây tối đa 180 phút, hoặc sẽ đá trong 15 phút tới
                                if -15 <= time_diff <= 180:
                                    is_live = True
                            except Exception:
                                is_live = True 
                        else:
                            # Không có thời gian hiển thị thì tìm dấu hiệu trận đang đá (số phút, tỉ số...)
                            if re.search(r'\d+\s*-\s*\d+', raw_text) or re.search(r"\d+'", raw_text) or "ĐANG ĐÁ" in raw_text or "HT" in raw_text or " VS " in raw_text:
                                is_live = True
                                
                        # Bỏ qua luôn trận này nếu phát hiện là trận tương lai
                        if not is_live:
                            continue
                            
                        # ==========================================
                        # 2. LÀM SẠCH TÊN TRẬN (Chỉ giữ Đội A vs Đội B)
                        # ==========================================
                        clean_name = raw_text
                        
                        # Xóa cụm giờ (VD: 23:00) và ngày (VD: 25-09)
                        clean_name = re.sub(r'\d{1,2}:\d{2}', '', clean_name)
                        clean_name = re.sub(r'\d{1,2}[-/]\d{1,2}([-/]\d{2,4})?', '', clean_name)
                        # Xóa cụm phút thi đấu (VD: 26')
                        clean_name = re.sub(r"\d+'", '', clean_name)
                        
                        # Xóa các từ thừa thải
                        for w in ['[LIVE]', 'LIVE', 'TRỰC TIẾP', 'BÓNG ĐÁ', 'XEM LẠI', 'SẮP DIỄN RA', 'HÔM NAY', 'GIẢI', 'VÒNG', 'BẢNG']:
                            clean_name = clean_name.replace(w, '')
                            
                        # Dọn dẹp ký tự rác (dấu gạch, khoảng trắng kép)
                        clean_name = re.sub(r'[\|\[\]]', '', clean_name)
                        clean_name = re.sub(r'^\s*[-:]*\s*', '', clean_name)
                        clean_name = re.sub(r'\s+', ' ', clean_name).strip()
                        
                        if not clean_name:
                            clean_name = href.split('/')[-1].replace('-', ' ').upper()
                        
                        if href not in match_dict:
                            match_dict[href] = clean_name
            
            print(f"Lọc được tổng cộng {len(match_dict)} trận đấu ĐANG DIỄN RA.")
            
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
                    
                    # Định dạng lại tên gọn gàng cho app M3U
                    playlist.append(f'#EXTINF:-1 group-title="Bóng Đá", {title}\n')
                    playlist.append(f'{stream_url}\n')
                    count += 1
                    print(f"-> Đã lấy thành công trận: {title}")
                    
            browser.close()
    except Exception as e:
        print(f"Lỗi tổng quan: {e}")

    if len(playlist) <= 1:
        playlist.append('#EXTINF:-1 group-title="Bóng Đá", Hiện chưa có trận đấu nào đang diễn ra\n')
        playlist.append('https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8\n')

    with open("xoilac_live.m3u", "w", encoding="utf-8") as f:
        f.writelines(playlist)
    print("Đã cập nhật danh sách M3U thành công!")

if __name__ == "__main__":
    main()
