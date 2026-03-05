"""
Main - Punto de entrada principal del juego Saint Seiya Battle Demo.
Inicia el servidor Flask y abre el navegador automáticamente.
"""
import os
import sys
import threading
import webbrowser
import time

# Agregar directorio del juego al path
GAME_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GAME_DIR)

from server import app


def open_browser():
    """Abre el navegador después de un breve delay."""
    time.sleep(1.5)
    webbrowser.open('http://localhost:5000')


if __name__ == '__main__':
    print("=" * 60)
    print("  ⚔️  SAINT SEIYA – BATTLE DEMO  ⚔️")
    print("=" * 60)
    print("  Iniciando servidor...")
    print("  Abre tu navegador en: http://localhost:5000")
    print("  Presiona Ctrl+C para salir")
    print("=" * 60)

    # Abrir navegador en hilo separado
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # Iniciar Flask
    app.run(debug=False, port=5000, host='0.0.0.0')
