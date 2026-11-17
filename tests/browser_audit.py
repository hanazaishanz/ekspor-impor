"""Optimasi aset dan audit Chrome tanpa dependensi Python tambahan.

Jalankan dengan --prepare-assets untuk membuat WebP dari PNG sumber imagegen.
Jalankan tanpa argumen untuk audit responsif, animasi, aksesibilitas, dan inquiry.
Browser berjalan headless, tidak membuka WhatsApp atau mengirim pesan sungguhan.
"""
import argparse
import base64
import hashlib
import http.server
import json
import os
import socket
import struct
import subprocess
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "preview"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *_args):
        pass


class CDP:
    """Klien WebSocket minimal untuk Chrome DevTools Protocol lokal."""
    def __init__(self, address):
        url = urllib.parse.urlsplit(address)
        self.sock = socket.create_connection((url.hostname, url.port), timeout=30)
        self.sock.settimeout(45)
        self.buffer = b""
        self.serial = 0
        self.events = []
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET {url.path} HTTP/1.1\r\nHost: {url.netloc}\r\n"
                           f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
                           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        while b"\r\n\r\n" not in self.buffer:
            self.buffer += self.sock.recv(65536)
        headers, self.buffer = self.buffer.split(b"\r\n\r\n", 1)
        if b" 101 " not in headers:
            raise RuntimeError(headers.decode())

    def take(self, count):
        while len(self.buffer) < count:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise RuntimeError("Chrome closed the connection")
            self.buffer += chunk
        value, self.buffer = self.buffer[:count], self.buffer[count:]
        return value

    def send(self, payload, opcode=1):
        if isinstance(payload, str):
            payload = payload.encode()
        length = len(payload)
        header = bytes([128 | opcode])
        if length < 126:
            header += bytes([128 | length])
        elif length < 65536:
            header += bytes([254]) + struct.pack("!H", length)
        else:
            header += bytes([255]) + struct.pack("!Q", length)
        mask = os.urandom(4)
        self.sock.sendall(header + mask + bytes(value ^ mask[index % 4] for index, value in enumerate(payload)))

    def receive(self):
        result = b""
        while True:
            first, second = self.take(2)
            length = second & 127
            if length == 126:
                length = struct.unpack("!H", self.take(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self.take(8))[0]
            mask = self.take(4) if second & 128 else None
            payload = self.take(length)
            if mask:
                payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
            if first & 15 == 9:
                self.send(payload, 10)
                continue
            if first & 15 == 8:
                raise RuntimeError("Chrome WebSocket closed")
            result += payload
            if first & 128:
                return json.loads(result)

    def call(self, method, params=None):
        self.serial += 1
        serial = self.serial
        self.send(json.dumps({"id": serial, "method": method, "params": params or {}}))
        while True:
            message = self.receive()
            if message.get("id") == serial:
                if "error" in message:
                    raise RuntimeError(str(message["error"]))
                return message.get("result", {})
            self.events.append(message)

    def evaluate(self, expression):
        result = self.call("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": True})
        if "exceptionDetails" in result:
            raise RuntimeError(json.dumps(result["exceptionDetails"]))
        return result.get("result", {}).get("value")

    def wait(self, milliseconds):
        # Tetap bekerja ketika emulasi browser mematikan JavaScript/timer halaman.
        time.sleep(milliseconds / 1000)

    def screenshot(self, name, full=True):
        size = self.call("Page.getLayoutMetrics")["cssContentSize"]
        params = {"format": "jpeg", "quality": 88, "captureBeyondViewport": full}
        if full:
            params["clip"] = {"x": 0, "y": 0, "width": size["width"], "height": size["height"], "scale": 1}
        result = self.call("Page.captureScreenshot", params)
        (OUT / name).write_bytes(base64.b64decode(result["data"]))


def prepare_assets(browser):
    """Konversi/resizing format menggunakan encoder WebP browser, bukan edit visual."""
    generated = []
    for name in ["briquette-cubes", "briquette-hexagonal", "briquette-packaging", "export-containers"]:
        source = ROOT / "preview" / "asset-sources" / f"{name}.png"
        data = base64.b64encode(source.read_bytes()).decode()
        widths = [480, 960] if name == "export-containers" else [640, 1280]
        for width in widths:
            expression = """new Promise((resolve,reject)=>{
              const image = new Image();
              image.onload=()=>{
                const canvas=document.createElement('canvas');
                canvas.width=WIDTH;canvas.height=Math.round(image.height*WIDTH/image.width);
                const context=canvas.getContext('2d');
                context.imageSmoothingQuality='high';context.drawImage(image,0,0,canvas.width,canvas.height);
                resolve({data:canvas.toDataURL('image/webp',.83),width:canvas.width,height:canvas.height});
              };
              image.onerror=()=>reject(new Error('Image decoding failed'));
              image.src=SOURCE;
            })""".replace("WIDTH", str(width)).replace("SOURCE", json.dumps("data:image/png;base64," + data))
            result = browser.evaluate(expression)
            content = base64.b64decode(result["data"].split(",", 1)[1])
            assert content[:4] == b"RIFF" and content[8:12] == b"WEBP", "Not WebP"
            path = ROOT / "assets" / "images" / f"{name}-{width}.webp"
            path.write_bytes(content)
            generated.append({"file": str(path.relative_to(ROOT)), "width": result["width"], "height": result["height"], "bytes": len(content)})
    (OUT / "asset-report.json").write_text(json.dumps(generated, indent=2), encoding="utf-8")
    print(json.dumps({"assets": generated}, ensure_ascii=False), flush=True)


def audit(browser, origin):
    results = []

    def check(name, passed, details=None):
        row = {"check": name, "passed": bool(passed)}
        if details is not None:
            row["details"] = details
        results.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)

    def viewport(width, height=900):
        browser.call("Emulation.setDeviceMetricsOverride", {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False})

    def navigate(path="/"):
        browser.call("Page.navigate", {"url": origin + path})
        for _ in range(100):
            if browser.evaluate("document.readyState") == "complete":
                break
            time.sleep(.1)
        browser.evaluate("document.fonts.ready.then(()=>true)")
        browser.wait(1200)

    viewport(1440)
    navigate()
    check("JavaScript initializes", browser.evaluate("document.documentElement.classList.contains('js') && !document.getElementById('inquiry-submit').disabled"))
    check("Local fonts load", browser.evaluate("document.fonts.check('800 40px Manrope') && document.fonts.check('400 15px Inter')"))
    check("All ten inquiry fields and five required fields", browser.evaluate("document.querySelectorAll('#inquiry-form input, #inquiry-form select, #inquiry-form textarea').length===10 && document.querySelectorAll('#inquiry-form [required]').length===5"))
    check("No placeholder links with empty # target", browser.evaluate("!document.querySelector('a[href=\"#\"]')"))

    # Audit semua breakpoint yang diwajibkan brief, termasuk seluruh halaman panjang.
    for width in [320, 375, 430, 768, 1024, 1366, 1440]:
        viewport(width, 850)
        browser.evaluate("window.scrollTo({top:0,behavior:'instant'})")
        browser.wait(250)
        browser.evaluate("""(async()=>{
          for(let y=0;y<document.documentElement.scrollHeight;y+=650){
            window.scrollTo({top:y,behavior:'instant'});await new Promise(r=>setTimeout(r,70));
          }
          window.scrollTo({top:0,behavior:'instant'});
        })()""")
        browser.wait(1100)
        measurements = browser.evaluate("""(()=>{
          const width=innerWidth;
          const fields=[...document.querySelectorAll('.field')].map(e=>e.getBoundingClientRect());
          return {
            viewport:width,scrollWidth:document.documentElement.scrollWidth,
            fieldsWithinViewport:fields.every(r=>r.left>=0 && r.right<=width+.5),
            columns:getComputedStyle(document.querySelector('.form-grid')).gridTemplateColumns,
            productColumns:getComputedStyle(document.querySelector('.products-grid')).gridTemplateColumns,
            brokenImages:[...document.images].filter(i=>!i.complete||!i.naturalWidth).map(i=>i.currentSrc),
            hiddenReveals:[...document.querySelectorAll('[data-reveal]')].filter(e=>getComputedStyle(e).opacity!=='1').length,
            sticky:getComputedStyle(document.getElementById('site-header')).position==='sticky'
          }
        })()""")
        check(f"Responsive {width}px", measurements["scrollWidth"] <= width and measurements["fieldsWithinViewport"] and not measurements["brokenImages"] and measurements["hiddenReveals"] == 0 and measurements["sticky"], measurements)
        if width == 375:
            browser.screenshot("website-mobile.jpeg")
            browser.screenshot("website-mobile-fold.jpeg", full=False)
        if width == 1440:
            browser.screenshot("website-desktop.jpeg")
            browser.screenshot("website-desktop-fold.jpeg", full=False)

    viewport(375)
    check("Mobile section headings retain word spacing", browser.evaluate("document.getElementById('about-title').textContent.includes('on briquettes. Built') && document.getElementById('services-title').textContent.includes('across your trade journey')"))
    browser.evaluate("document.getElementById('full-name').focus()")
    browser.wait(250)
    check("Floating contact does not cover mobile typing", browser.evaluate("document.getElementById('floating-whatsapp').inert && getComputedStyle(document.getElementById('floating-whatsapp')).visibility==='hidden'"))
    browser.evaluate("document.getElementById('full-name').blur();window.scrollTo({top:0,behavior:'instant'})")
    browser.wait(250)
    browser.evaluate("document.getElementById('menu-toggle').click()")
    browser.wait(400)
    check("Mobile menu opens and becomes accessible", browser.evaluate("document.getElementById('menu-toggle').getAttribute('aria-expanded')==='true' && !document.getElementById('site-nav').inert && document.querySelector('.nav-link').getBoundingClientRect().height>=44"))
    browser.call("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Escape", "code": "Escape"})
    check("Escape closes menu and restores focus", browser.evaluate("document.getElementById('menu-toggle').getAttribute('aria-expanded')==='false' && document.getElementById('site-nav').inert && document.activeElement.id==='menu-toggle'"))
    browser.evaluate("document.getElementById('menu-toggle').click(); document.querySelector('.nav-link[href=\"#products\"]').click()")
    browser.wait(800)
    check("Navigation link closes mobile menu", browser.evaluate("document.getElementById('menu-toggle').getAttribute('aria-expanded')==='false' && location.hash==='#products'"))
    viewport(1440)
    browser.wait(200)
    check("Desktop navigation restores after resize", browser.evaluate("!document.getElementById('site-nav').inert && !document.getElementById('site-nav').hasAttribute('aria-hidden')"))

    # Semua panggilan WhatsApp ditangkap; tidak ada popup atau pesan nyata.
    browser.evaluate("window.__openCalls=[];window.open=(...args)=>{window.__openCalls.push(args);return null};")
    browser.evaluate("document.getElementById('inquiry-form').reset();document.getElementById('inquiry-form').requestSubmit()")
    check("Empty required fields blocked and first error focused", browser.evaluate("window.__openCalls.length===0 && document.querySelectorAll('[aria-invalid=true]').length===4 && document.activeElement.id==='full-name'"))
    browser.evaluate("""(()=>{
      const f=document.getElementById('inquiry-form');
      f.elements.fullName.value='   ';f.elements.company.value='Audit Company';
      f.elements.email.value='wrong-email';f.elements.commodity.value='Cube briquettes';
      f.requestSubmit();
    })()""")
    check("Whitespace name and invalid email blocked", browser.evaluate("window.__openCalls.length===0 && document.getElementById('full-name').getAttribute('aria-invalid')==='true' && document.getElementById('email').getAttribute('aria-invalid')==='true'"))
    browser.evaluate("""(()=>{
      const f=document.getElementById('inquiry-form');
      const values={fullName:'Audit Buyer',company:'Audit & Co',email:'audit@example.test',phone:'+1 202 555 0123',service:'Export',quantity:'10 tonnes',commodity:'Cube & hexagonal briquettes',origin:'Origin test',destination:'Destination test',notes:'Line one & details\\nLine two — café'};
      Object.entries(values).forEach(([k,v])=>f.elements[k].value=v);f.requestSubmit();
    })()""")
    check("Unconfigured WhatsApp blocks external navigation", browser.evaluate("window.__openCalls.length===0 && document.getElementById('form-status').textContent.includes('not been added')"))
    browser.evaluate("window.SITE_CONFIG.whatsappNumber='12025550123';document.getElementById('inquiry-form').requestSubmit()")
    inquiry = browser.evaluate("""(()=>{
      const call=window.__openCalls[0];const url=new URL(call[0]);const text=url.searchParams.get('text');
      return {url:call[0],target:call[1],features:call[2],message:text,fallback:!document.getElementById('whatsapp-fallback').hidden,errors:document.querySelectorAll('[aria-invalid=true]').length};
    })()""")
    check("Encoded WhatsApp inquiry includes all ten fields", all(value in inquiry["message"] for value in ["Audit Buyer", "Audit & Co", "audit@example.test", "+1 202 555 0123", "Service Type: Export", "Cube & hexagonal briquettes", "10 tonnes", "Origin test", "Destination test", "Line one & details\nLine two — café"]) and inquiry["url"].startswith("https://wa.me/12025550123?text=") and "%26" in inquiry["url"] and "%0A" in inquiry["url"], {"encoded": True, "allFields": True})
    check("Popup protection and usable fallback link", inquiry["target"] == "_blank" and "noopener" in inquiry["features"] and inquiry["fallback"] and inquiry["errors"] == 0)
    browser.evaluate("document.getElementById('floating-whatsapp').click()")
    check("Floating WhatsApp uses the same configured number", browser.evaluate("window.__openCalls.length===2 && window.__openCalls[1][0].startsWith('https://wa.me/12025550123?text=')"))
    browser.evaluate("document.getElementById('notes').dispatchEvent(new Event('input',{bubbles:true}))")
    check("Editing an inquiry invalidates the old fallback link", browser.evaluate("document.getElementById('whatsapp-fallback').hidden && !document.getElementById('whatsapp-fallback-link').hasAttribute('href')"))
    browser.evaluate("window.SITE_CONFIG.whatsappNumber='';document.getElementById('inquiry-form').reset();document.querySelector('[data-inquiry-product=\"Hexagonal Briquettes\"]').click()")
    browser.wait(700)
    check("Product inquiry prefills form and focuses product field", browser.evaluate("document.getElementById('commodity').value==='Hexagonal Briquettes' && document.getElementById('service-type').value==='Export' && document.activeElement.id==='commodity'"))
    browser.evaluate("document.querySelector('[data-inquiry-service=\"Import\"]').click()")
    check("Service inquiry selects Import", browser.evaluate("document.getElementById('service-type').value==='Import'"))
    browser.wait(650)
    browser.evaluate("document.getElementById('notes').value='Existing notes';document.querySelector('[data-inquiry-note]').click()")
    check("Service notes preserve visitor input", browser.evaluate("document.getElementById('notes').value.startsWith('Existing notes\\n')"))
    browser.wait(650)
    browser.evaluate("document.getElementById('inquiry-form').reset();window.scrollTo({top:0,behavior:'instant'});document.activeElement.blur()")
    browser.wait(300)
    browser.evaluate("document.querySelector('[data-slide=\"0\"]').click()")
    initial = browser.evaluate("document.querySelector('.slide-dot.is-active').dataset.slide")
    browser.wait(6250)
    advanced = browser.evaluate("document.querySelector('.slide-dot.is-active').dataset.slide")
    check("Hero slideshow automatically advances", initial != advanced)
    browser.evaluate("document.getElementById('slideshow-pause').click()")
    paused = browser.evaluate("document.querySelector('.slide-dot.is-active').dataset.slide")
    browser.wait(6250)
    check("Pause stops autoplay", browser.evaluate("document.querySelector('.slide-dot.is-active').dataset.slide") == paused)
    browser.evaluate("document.querySelector('[data-slide=\"2\"]').click()")
    check("Manual slide controls work while paused", browser.evaluate("document.querySelector('.slide-dot.is-active').dataset.slide==='2' && document.querySelectorAll('.hero-slide[aria-hidden=false]').length===1"))
    browser.call("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "reduce"}]})
    browser.wait(250)
    check("Reduced motion disables autoplay, zoom and hidden reveals", browser.evaluate("!document.documentElement.classList.contains('motion-ready') && document.getElementById('slideshow-pause').disabled && getComputedStyle(document.querySelector('.hero-slide.is-active img')).animationName==='none' && getComputedStyle(document.documentElement).scrollBehavior==='auto'"))
    check("No visitor information stored", browser.evaluate("localStorage.length===0 && sessionStorage.length===0 && document.cookie===''"))

    # Konten dan navigasi tetap terbaca jika JavaScript dimatikan.
    browser.call("Emulation.setScriptExecutionDisabled", {"value": True})
    viewport(375)
    navigate()
    check("No-JavaScript content and navigation remain available", browser.evaluate("getComputedStyle(document.querySelector('.hero-copy')).opacity==='1' && getComputedStyle(document.getElementById('menu-toggle')).display==='none' && getComputedStyle(document.getElementById('site-nav')).visibility==='visible' && document.getElementById('inquiry-submit').disabled"))
    browser.call("Emulation.setScriptExecutionDisabled", {"value": False})

    failures = []
    for event in browser.events:
        if event.get("method") == "Runtime.exceptionThrown":
            failures.append(event["params"].get("exceptionDetails"))
        elif event.get("method") == "Network.responseReceived" and event["params"]["response"]["status"] >= 400:
            failures.append({"status": event["params"]["response"]["status"], "url": event["params"]["response"]["url"]})
    check("No JavaScript exceptions or failed HTTP assets", not failures, failures)
    (OUT / "audit-report.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    passed = sum(item["passed"] for item in results)
    print(json.dumps({"passed": passed, "total": len(results), "report": str(OUT / "audit-report.json")}), flush=True)
    return passed == len(results)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-assets", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    if not chrome.exists():
        chrome = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    with tempfile.TemporaryDirectory(prefix="briquette-audit-") as profile:
        process = subprocess.Popen([str(chrome), "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--disable-background-networking", "--remote-debugging-port=0", f"--user-data-dir={profile}", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        browser = None
        try:
            port_file = Path(profile) / "DevToolsActivePort"
            for _ in range(150):
                if port_file.exists():
                    break
                if process.poll() is not None:
                    raise RuntimeError("Chrome exited before becoming ready")
                time.sleep(.1)
            port = int(port_file.read_text().splitlines()[0])
            request = urllib.request.Request(f"http://127.0.0.1:{port}/json/new?about:blank", method="PUT")
            with urllib.request.urlopen(request, timeout=15) as response:
                target = json.load(response)
            browser = CDP(target["webSocketDebuggerUrl"])
            for domain in ["Page", "Runtime", "Network", "Log"]:
                browser.call(domain + ".enable")
            # Tab headless perlu fokus aktif agar event focusin/focusout sama dengan browser pengguna.
            browser.call("Page.bringToFront")
            browser.call("Emulation.setFocusEmulationEnabled", {"enabled": True})
            if args.prepare_assets:
                prepare_assets(browser)
                success = True
            else:
                success = audit(browser, origin)
        finally:
            if browser:
                try:
                    browser.call("Browser.close")
                except (OSError, RuntimeError):
                    pass
                browser.sock.close()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)
            server.shutdown()
            server.server_close()
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
