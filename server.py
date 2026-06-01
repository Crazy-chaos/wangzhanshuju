import os
import http.server
import socketserver
import urllib.parse
import ssl

# 确保服务器的工作目录始终是当前脚本所在的目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

PORT = 443

class RangeRequestHandler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith('/'):
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                self.send_error(403, "Directory listing is forbidden")
                return None
                
        # 安全限制：只允许访问特定的文件类型，防止暴露源码等敏感文件
        allowed_extensions = ['.html', '.htm', '.mp4', '.zip', '.js', '.webp', '.avif', '.jpg', '.jpeg', '.gif', '.png']
        if not any(path.lower().endswith(ext) for ext in allowed_extensions):
            self.send_error(403, "Access to this file type is forbidden")
            return None
            
        ctype = self.guess_type(path)
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(404, "File not found")
            return None

        try:
            fs = os.fstat(f.fileno())
            size = fs.st_size

            if "Range" in self.headers:
                # 处理 Range 请求（即视频拖拽进度条）
                self.send_response(206)
                self.send_header("Content-type", ctype)
                self.send_header("Accept-Ranges", "bytes")

                range_header = self.headers.get("Range").strip()
                range_header = range_header.replace("bytes=", "")
                ranges = range_header.split("-")
                
                if ranges[0] and ranges[1]:
                    start = int(ranges[0])
                    end = int(ranges[1])
                elif ranges[0]:
                    start = int(ranges[0])
                    end = size - 1
                elif ranges[1]:
                    start = size - int(ranges[1])
                    end = size - 1
                else:
                    start = 0
                    end = size - 1

                self.range_start = start
                self.range_length = end - start + 1

                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                self.send_header("Content-Length", str(self.range_length))
                if path.endswith('.mp4') or path.endswith('.zip'):
                    self.send_header("Cache-Control", "public, max-age=604800")
                self.end_headers()
                return f
            else:
                self.send_response(200)
                self.send_header("Content-type", ctype)
                self.send_header("Content-Length", str(size))
                self.send_header("Accept-Ranges", "bytes")
                if path.endswith('.mp4') or path.endswith('.zip'):
                    self.send_header("Cache-Control", "public, max-age=604800")
                elif path.endswith('.html') or path.endswith('.js'):
                    self.send_header("Cache-Control", "public, max-age=3600")
                self.end_headers()
                self.range_start = None
                return f
        except Exception:
            f.close()
            raise

    def do_GET(self):
        f = self.send_head()
        if f:
            try:
                # 根据范围返回特定字节，实现视频可以随意拖拽
                if getattr(self, 'range_start', None) is not None:
                    f.seek(self.range_start)
                    length = self.range_length
                    while length > 0:
                        buf = f.read(min(length, 64 * 1024))
                        if not buf:
                            break
                        self.wfile.write(buf)
                        length -= len(buf)
                else:
                    self.copyfile(f, self.wfile)
            except Exception as e:
                # 客户端断开连接时可能会抛出异常，忽略即可
                pass
            finally:
                f.close()

if __name__ == '__main__':
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    import os
    
    # 智能端口与协议判断：如果没有证书，不要强行使用 443 提供 HTTP 服务，否则浏览器会拦截
    if os.path.exists('cert.pem') and os.path.exists('key.pem'):
        use_ssl = True
        actual_port = PORT
        protocol = "https"
    else:
        use_ssl = False
        actual_port = 5555 if PORT == 443 else PORT
        protocol = "http"
        
    with socketserver.ThreadingTCPServer(("", actual_port), RangeRequestHandler) as httpd:
        if use_ssl:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
            httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

        print(f"===================================================")
        print(f"带【视频进度条支持】与【网络缓存加速】的服务器已启动")
        print(f"监听端口: {actual_port} ({protocol.upper()})")
        print(f"本地访问地址: {protocol}://localhost:{actual_port}")
        print(f"===================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已关闭。")
