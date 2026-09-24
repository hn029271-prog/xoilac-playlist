import requests
from bs4 import BeautifulSoup

# Trang web nguồn cần cào dữ liệu
URL = "https://xoiche.tv/"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_matches():
    playlist = ["#EXTM3U\n"]
    try:
        response = requests.get(URL, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Không thể truy cập trang web, mã lỗi: {response.status_code}")
            return playlist

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tìm các khối chứa thông tin trận đấu (thường là các thẻ chứa lịch thi đấu/trực tiếp)
        # Tùy thuộc vào giao diện thực tế của trang, ta quét các khối trận đấu
        match_items = soup.find_all('div', class_='match-item') # Hoặc cấu trúc thẻ tương ứng
        
        # Nếu trang web thay đổi cấu trúc class, ta quét tất cả các đường dẫn trận đấu có chứa từ khóa
        if not match_items:
            # Quét rộng hơn để bắt các thẻ a hoặc div có chứa link trận đấu
            links = soup.find_all('a', href=True)
            match_links = [l['href'] for l in links if '/match/' in l['href'] or 'tran-dau' in l['href']]
            match_links = list(set(match_links)) # Lọc trùng
            
            if match_links:
                for link in match_links[:10]: # Lấy tối đa 10 trận đang hot
                    if not link.startswith('http'):
                        match_link = "https://xoiche.tv" + link
                    else:
                        match_link = link
                    
                    # Tạo tên hiển thị cho trận đấu dựa vào đường dẫn
                    match_name = link.split('/')[-1].replace('-', ' ').upper()
                    if not match_name:
                        match_name = "TRAN DAU TRUC TIEP"
                        
                    playlist.append(f'#EXTINF:-1 group-title="Bóng Đá Trực Tiếp", [LIVE] {match_name}\n')
                    playlist.append(f'{match_link}\n')
        else:
            for item in match_items:
                # Trích xuất tên đội bóng hoặc tên trận đấu
                title_elem = item.find('div', class_='teams')
                title = title_elem.text.strip() if title_elem else "Trận đấu trực tiếp"
                title = " ".join(title.split()) # Xóa khoảng trắng thừa
                
                # Lấy link chi tiết hoặc link stream trực tiếp bên trong
                a_tag = item.find('a', href=True)
                if a_tag:
                    link = a_tag['href']
                    if not link.startswith('http'):
                        link = "https://xoiche.tv" + link
                        
                    playlist.append(f'#EXTINF:-1 group-title="Bóng Đá Trực Tiếp", [LIVE] {title}\n')
                    playlist.append(f'{link}\n')

    except Exception as e:
        print(f"Lỗi trong quá trình cào dữ liệu: {e}")

    return playlist

def save_playlist():
    playlist = get_matches()
    # Nếu không quét được trận nào (ví dụ ngoài giờ thi đấu), giữ lại cấu trúc chuẩn M3U
    if len(playlist) <= 1:
        print("Không tìm thấy trận đấu nào đang diễn ra hoặc cấu trúc trang đã thay đổi.")
    
    with open("xoilac_live.m3u", "w", encoding="utf-8") as f:
        f.writelines(playlist)
    print("Đã cập nhật file xoilac_live.m3u thành công!")

if __name__ == "__main__":
    save_playlist()
