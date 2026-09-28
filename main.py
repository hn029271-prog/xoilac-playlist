import os
import re
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

M3U_FILE = "xoilac_live.m3u"
BASE_DOMAIN = "https://xoiche1.live"

def clean_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', str(text)).strip()

def format_title(raw_text):
    text = clean_text(raw_text)
    
    # Loại bỏ ngày giờ (VD: 23:00 | 28-09)
    text = re.sub(r'\d{1,2}:\d{2}\s*\|\s*\d{1,2}-\d{1,2}(-\d{2,4})?', '', text)
    text = re.sub(r'\d{1,2}:\d{2}', '', text)
    text = clean_text(text)

    # Tìm phút thi đấu
    minute_match = re.search(r"(\d+['′]|Hiệp \d|H\d|HT)", text, re.IGNORECASE)
    minute_str = ""
    if minute_match:
        minute_str = minute_match.group(1)
        text = text.replace(minute_str, '').strip()

    if not minute_str:
        return None

    # Dọn dẹp từ thừa
    text = re.sub(r'^(Trực tiếp|Live|Xem|TRỰC TIẾP)\s+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+(blv|BLV).*$', '', text, flags=re.IGNORECASE)

    return f"{text} | {minute_str}"

async def capture_m3u8(context, match_url):
    """
    Mở từng trận trong một Tab (Page) hoàn toàn mới 
    để không bị lẫn request giữa các trận với nhau.
    """
    page = await context.new_page()
    found_m3u8 = None

    def handle_request(request):
        nonlocal found_m3u8
        url = request.url
        # Chỉ bắt link stream m3u8 thật, bỏ qua quảng cáo
        if '.m3u8' in url and not any(x in url.lower() for x in ['ad', 'promo', 'banner', 'analytics']):
            if not found_m3u8:
                found_m3u8 = url

    page.on("request", handle_request)

    try:
        print(f"Đang mở trình duyệt ảo: {match_url}")
        await page.goto(match_url, timeout=25000, wait_until="domcontentloaded")
        
        # Click giả lập vào màn hình video để kích hoạt luồng phát
        try:
            await page.click("video, iframe, .player-wrapper", timeout=3000)
        except:
            pass

        # Tăng thời gian chờ lên 12 giây (24 lần x 0.5s) để đợi quảng cáo chạy xong
        for _ in range(24):
            if found_m3u8:
                break
            await asyncio.sleep(0.5)

    except Exception as e:
        print(f"Lỗi khi bắt stream từ {match_url}: {e}")

    await page.close() # Đóng tab sau khi hoàn thành
    return found_m3u8 or match_url

async def main():
    matches = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print(f"Đang quét danh sách trận đấu từ {BASE_DOMAIN}...")
        try:
            await page.goto(BASE_DOMAIN, timeout=20000, wait_until="networkidle")
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            links = soup.find_all('a', href=True)
            seen_urls = set()

            raw_matches = []
            for a in links:
                href = a['href']
                if '/truc-tiep/' in href:
                    full_url = href if href.startswith("http") else f"{BASE_DOMAIN.rstrip('/')}/{href.lstrip('/')}"
                    base_url = re.sub(r'\?blv=.*$', '', full_url)

                    if base_url in seen_urls:
                        continue
                    
                    raw_text = a.get_text(separator=" ")
                    title = format_title(raw_text)

                    if title:
                        seen_urls.add(base_url)
                        raw_matches.append((title, base_url))

            print(f"==> Tìm thấy {len(raw_matches)} trận đang LIVE. Bắt đầu giải mã .m3u8...")

            # ĐÂY LÀ ĐOẠN ĐÃ SỬA: Truyền `context` vào thay vì `page`
            for title, url in raw_matches:
                m3u8_url = await capture_m3u8(context, url)
                print(f" -> Trận: {title}")
                print(f"    Stream: {m3u8_url}")
                matches.append((title, m3u8_url))

        except Exception as e:
            print(f"Lỗi truy cập trang chủ: {e}")
        
        await browser.close()

    # Ghi ra file M3U
    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        if not matches:
            f.write('#EXTINF:-1 tvg-logo="" group-title="Bóng Đá", [LIVE] Hiện không có trận đấu nào đang đá\n')
            f.write("https://example.com/live.m3u8\n")
        else:
            for title, stream_url in matches:
                f.write(f'#EXTINF:-1 tvg-logo="" group-title="Bóng Đá", {title}\n')
                f.write(f'{stream_url}\n')

if __name__ == "__main__":
    asyncio.run(main())
