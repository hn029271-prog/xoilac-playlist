import requests
from bs4 import BeautifulSoup
import re

URL = "https://xoiche.tv/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_realtime_matches():
    playlist = ["#EXTM3U\n"]
    try:
        response = requests.get(URL, headers=headers, timeout=10)
        if response.status_code != 200:
            print("Không thể kết nối đến trang web nguồn.")
            return playlist

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Lấy tất cả các đường dẫn trận đấu từ trang chủ
        links = soup.find_all('a', href=True)
        match_dict = {}
        
        for l in links:
            href = l['href']
            if '/tran-dau/' in href or '/match/' in href:
                if not href.startswith('http'):
                    match_url = "https://xoiche.tv" + href
                else:
                    match_url = href
                
                # Lấy tên hiển thị của trận đấu từ text của thẻ hoặc từ URL
                title = l.get_text(strip=True)
                if not title or len(title) < 3:
                    title = href.split('/')[-1].replace('-', ' ').upper()
                
                match_dict[match_url] = title

        # Duyệt qua các trận tìm được để quét link .m3u8 thực tế bên trong trang chi tiết
        count = 0
        for match_url, title in match_dict.items():
            if count >= 10:  # Giới hạn lấy tối đa 10 trận để kịch bản chạy nhanh
                break
            try:
                detail_resp = requests.get(match_url, headers=headers, timeout=5)
                if detail_resp.status_code == 200:
                    # Tìm kiếm link .m3u8 ẩn trong mã nguồn trang chi tiết trận đấu
                    m3u8_matches = re.findall(r'https?://[^\s<>"]+?\.m3u8[^\s<>"]*', detail_resp.text)
                    if m3u8_matches:
                        stream_url = m3u8_matches[0]
                        # Thêm vào danh sách phát với tên thật và link .m3u8 chuẩn
                        playlist.append(f'#EXTINF:-1 group-title="Bóng Đá Trực Tiếp", [LIVE] {title}\n')
                        playlist.append(f'{stream_url}\n')
                        count += 1
            except Exception:
                continue

    except Exception as e:
        print(f"Lỗi trong quá trình quét dữ liệu: {e}")

    return playlist

def save_playlist():
    playlist = get_realtime_matches()
    
    # Nếu thời điểm này chưa cào được link stream (hoặc ngoài giờ thi đấu), giữ lại thông báo để máy không bị lỗi trống
    if len(playlist) <= 1:
        playlist.append('#EXTINF:-1 group-title="Bóng Đá Trực Tiếp", [THÔNG BÁO] Hiện chưa có trận đang phát trực tiếp\n')
        playlist.append('https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8\n')
        
    with open("xoilac_live.m3u", "w", encoding="utf-8") as f:
        f.writelines(playlist)
    print("Đã cập nhật file xoilac_live.m3u thành công!")

if __name__ == "__main__":
    save_playlist()
