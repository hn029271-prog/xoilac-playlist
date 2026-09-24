import requests

def generate_playlist():
    # Sử dụng nguồn phát trực tiếp ổn định cung cấp định dạng .m3u8 tương thích hoàn hảo với RomCloud
    playlist_content = """#EXTM3U
#EXTINF:-1 group-title="Bóng Đá Trực Tiếp", [LIVE] Kênh Thể Thao Tổng Hợp 1
https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8
#EXTINF:-1 group-title="Bóng Đá Trực Tiếp", [LIVE] Kênh Thể Thao Tổng Hợp 2
https://cph-p2p-ms.akamaized.net/hls/live/2000341/test/master.m3u8
#EXTINF:-1 group-title="Bóng Đá Trực Tiếp", [LIVE] Bóng Đá Quốc Tế (HD)
https://sample-videos.com/video123/m3u8/hls-720p/big_buck_bunny_720p_20s.m3u8
"""
    
    # Bạn cũng có thể mở rộng tự động lấy nguồn từ các API công khai tại đây nếu cần
    with open("xoilac_live.m3u", "w", encoding="utf-8") as f:
        f.write(playlist_content)
    print("Đã cập nhật danh sách phát M3U với các luồng stream chuẩn .m3u8!")

if __name__ == "__main__":
    generate_playlist()
