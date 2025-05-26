import base64
import http.server
import os
import socket
import socketserver
import ssl
import threading
import urllib.parse


class URL:
    isFile = False
    is_base64 = False

    @staticmethod
    def fileserver(path):
        os.chdir(path)
        PORT = 8000
        Handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"Serving at http://localhost:{PORT}/ from {path}")
            httpd.serve_forever()

    def __init__(self, url):
        self.scheme, url = url.split(":", 1)
        assert self.scheme in ["http", "https", "file", "data"]
        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443
        elif self.scheme == "file":
            URL.isFile = True
            url = url.strip("/", 2)
            self.fileserver(url)
            return
        elif self.scheme == "data":
            self.host = None
            self.port = None
            metadata, self.content = url.split(",", 1)
            self.mediatype = "text/plain"
            if ";" in self.mediatype:
                parts = metadata.split(";")
                self.mediatype = parts[0] if parts[0] else "text/plain"
                URL.is_base64 = "base64" in parts
            elif metadata:
                self.mediatype = metadata
            return
        url = url.strip("/", 2)
        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1)
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)
        self.path = "/" + url

    def request(self):
        if self.scheme == "data":
            data = self.content
            if URL.is_base64:
                decoded = base64.b64decode(data)
                return decoded.decode("utf8", errors="replace")
            else:
                return urllib.parse.unquote(data)
        s = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
        )
        s.connect((self.host, self.port))
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
        request = "GET {} HTTP/1.0\r\n".format(self.path)
        request += "Host: {} \r\n".format(self.host)
        headers = {
            "User-Agent": "Mubsurf",
            "Connection": "close",
        }
        for key, value in headers.items():
            request += "{}: {}\r\n".format(key, value)
        request += "\r\n"
        print(request)
        s.send(request.encode("utf8"))
        response = s.makefile("r", encoding="utf8", newline="\r\n")
        status_line = response.readline()
        version, status, explanation = status_line.split(" ", 2)
        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers
        content = response.read()
        s.close()
        return content

    @staticmethod
    def show(body):
        in_tag = False
        for c in body:
            if c == "<":
                in_tag = True
            elif c == ">":
                in_tag = False
            elif not in_tag:
                print(c, end="")

    @staticmethod
    def load(url):
        if URL.isFile:
            return
        body = url.request()
        URL.show(body)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        URL.fileserver("/home/conste/repos/mini-browser/")
        # URL.load(URL("http://localhost:8000/index.html"))
    else:
        URL.load(URL(sys.argv[1]))
