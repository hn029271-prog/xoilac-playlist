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
