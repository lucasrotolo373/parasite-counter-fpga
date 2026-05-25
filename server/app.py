%%writefile /home/xilinx/start_parasite.py
import os
import subprocess
import time
from flask import Flask, send_file, jsonify

print("Iniciando secuencia segura de Wi-Fi...")
subprocess.run(['sudo', 'ip', 'addr', 'flush', 'dev', 'wlan0'])
subprocess.run(['sudo', 'ip', 'addr', 'add', '192.168.4.1/24', 'dev', 'wlan0'])
subprocess.run(['sudo', 'hostapd', '-B', '/etc/hostapd/hostapd.conf'])
time.sleep(2)
subprocess.run(['sudo', 'systemctl', 'start', 'dnsmasq'])
print("Wi-Fi y DHCP encendidos.")

app = Flask(_name_)

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta charset="UTF-8">
        <style>
            body { margin: 0; background: #000; display: flex; flex-direction: column; align-items: center; font-family: Arial, sans-serif; }
            h1 { color: white; font-size: 2em; margin: 20px 0 10px 0; }
            img { width: 100%; max-width: 640px; }
            p { color: #aaa; font-size: 0.9em; }
        </style>
        <script>
            function actualizarConteo() { fetch('/conteo').then(r => r.json()).then(d => { document.getElementById('conteo').innerText = 'Huevos: ' + d.huevos; }); }
            function actualizarImagen() { document.getElementById('resultado').src = '/imagen?' + new Date().getTime(); }
            setInterval(function() { actualizarConteo(); actualizarImagen(); }, 2000);
        </script>
    </head>
    <body>
        <h1 id="conteo">Esperando captura...</h1>
        <img id="resultado" src="/imagen" />
        <p>Actualización automática</p>
    </body>
    </html>
    '''

@app.route('/imagen')
def imagen():
    if os.path.exists('/tmp/resultado.png'):
        return send_file('/tmp/resultado.png', mimetype='image/png')
    return '', 204

@app.route('/conteo')
def conteo():
    if os.path.exists('/tmp/conteo.txt'):
        with open('/tmp/conteo.txt') as f:
            return jsonify({"huevos": int(f.read().strip())})
    return jsonify({"huevos": "—"})

if _name_ == '_main_':
    app.run(host='0.0.0.0', port=5000, debug=False)