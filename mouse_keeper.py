#!/usr/bin/env python3
"""
Mouse Keeper - Mantém o computador ativo simulando movimento e cliques periódicos.

Por padrão, atua em uma pequena área restrita de 2cm x 2cm na região escolhida da tela,
mantendo o cursor quase no mesmo local sem atrapalhar o usuário.

Suporta macOS nativamente (sem necessidade de instalar pacotes externos)
e também conta com suporte PyAutoGUI para outros ambientes.
"""

import sys
import os
import time
import math
import random
import argparse
from datetime import datetime

# ==============================================================================
# Controlador de Mouse (Nativo macOS via CoreGraphics com fallback PyAutoGUI)
# ==============================================================================

class MacOSMouseController:
    """Controlador nativo para macOS usando CoreGraphics via ctypes (Zero dependências)."""

    def __init__(self):
        import ctypes
        from ctypes import c_double, Structure, c_void_p, c_uint32, c_size_t

        class CGPoint(Structure):
            _fields_ = [("x", c_double), ("y", c_double)]

        self.CGPoint = CGPoint
        self.cg = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        self.cf = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")

        # Resolução de tela
        self.cg.CGMainDisplayID.restype = c_uint32
        self.cg.CGDisplayPixelsWide.argtypes = [c_uint32]
        self.cg.CGDisplayPixelsWide.restype = c_size_t
        self.cg.CGDisplayPixelsHigh.argtypes = [c_uint32]
        self.cg.CGDisplayPixelsHigh.restype = c_size_t

        # Posição atual
        self.cg.CGEventCreate.restype = c_void_p
        self.cg.CGEventGetLocation.argtypes = [c_void_p]
        self.cg.CGEventGetLocation.restype = CGPoint

        # Criação e postagem de eventos
        self.cg.CGEventCreateMouseEvent.argtypes = [c_void_p, c_uint32, CGPoint, c_uint32]
        self.cg.CGEventCreateMouseEvent.restype = c_void_p
        self.cg.CGEventPost.argtypes = [c_uint32, c_void_p]
        self.cf.CFRelease.argtypes = [c_void_p]

        # Constantes CoreGraphics
        self.kCGEventMouseMoved = 5
        self.kCGEventLeftMouseDown = 1
        self.kCGEventLeftMouseUp = 2
        self.kCGMouseButtonLeft = 0
        self.kCGHIDEventTap = 0

    def get_screen_size(self):
        main_id = self.cg.CGMainDisplayID()
        return self.cg.CGDisplayPixelsWide(main_id), self.cg.CGDisplayPixelsHigh(main_id)

    def get_position(self):
        ev = self.cg.CGEventCreate(None)
        if not ev:
            return 0.0, 0.0
        loc = self.cg.CGEventGetLocation(ev)
        self.cf.CFRelease(ev)
        return float(loc.x), float(loc.y)

    def move_instant(self, x: float, y: float):
        pt = self.CGPoint(x, y)
        ev = self.cg.CGEventCreateMouseEvent(None, self.kCGEventMouseMoved, pt, self.kCGMouseButtonLeft)
        if ev:
            self.cg.CGEventPost(self.kCGHIDEventTap, ev)
            self.cf.CFRelease(ev)

    def move_to(self, target_x: float, target_y: float, duration: float = 0.4):
        """Move o mouse suavemente até o destino (interpolação)."""
        if duration <= 0:
            self.move_instant(target_x, target_y)
            return

        start_x, start_y = self.get_position()
        steps = max(12, int(duration * 60))
        sleep_interval = duration / steps

        for i in range(1, steps + 1):
            t = i / steps
            # Suavização Ease-in-out (smoothstep)
            t_smooth = t * t * (3 - 2 * t)
            curr_x = start_x + (target_x - start_x) * t_smooth
            curr_y = start_y + (target_y - start_y) * t_smooth
            self.move_instant(curr_x, curr_y)
            time.sleep(sleep_interval)

    def click(self):
        cur_x, cur_y = self.get_position()
        pt = self.CGPoint(cur_x, cur_y)

        # Mouse Down
        ev_down = self.cg.CGEventCreateMouseEvent(None, self.kCGEventLeftMouseDown, pt, self.kCGMouseButtonLeft)
        if ev_down:
            self.cg.CGEventPost(self.kCGHIDEventTap, ev_down)
            self.cf.CFRelease(ev_down)

        time.sleep(0.05)

        # Mouse Up
        ev_up = self.cg.CGEventCreateMouseEvent(None, self.kCGEventLeftMouseUp, pt, self.kCGMouseButtonLeft)
        if ev_up:
            self.cg.CGEventPost(self.kCGHIDEventTap, ev_up)
            self.cf.CFRelease(ev_up)


class PyAutoGUIMouseController:
    """Controlador via biblioteca PyAutoGUI (multiplataforma)."""

    def __init__(self):
        import pyautogui
        self.pag = pyautogui
        self.pag.FAILSAFE = True

    def get_screen_size(self):
        return self.pag.size()

    def get_position(self):
        return self.pag.position()

    def move_to(self, target_x: float, target_y: float, duration: float = 0.4):
        self.pag.moveTo(target_x, target_y, duration=duration)

    def click(self):
        self.pag.click()


def get_mouse_controller():
    """Detecta e retorna o melhor controlador disponível."""
    if sys.platform == "darwin":
        try:
            return MacOSMouseController(), "macOS Nativo (CoreGraphics)"
        except Exception:
            pass

    try:
        return PyAutoGUIMouseController(), "PyAutoGUI"
    except ImportError:
        print("[ERRO] Não foi possível inicializar o controlador de mouse.")
        print("Instale o pyautogui: pip install pyautogui")
        sys.exit(1)


# ==============================================================================
# Cálculo e Mapeamento de Áreas
# ==============================================================================

def cm_to_pixels(cm: float, dpi: float = 100.0) -> int:
    """
    Converte centímetros para pixels baseado no DPI médio da tela.
    Para telas normais/retina de desktop, 100 DPI representa aproximadamente
    40 pixels por centímetro (2.0 cm ≈ 80 pixels).
    """
    inches = cm / 2.54
    return max(10, int(round(inches * dpi)))


def get_area_bounds(
    area_name: str,
    screen_w: int,
    screen_h: int,
    box_size_px: int = 80,
    padding: int = 60,
    full_quadrant: bool = False
):
    """
    Calcula as coordenadas de limite (x_min, x_max, y_min, y_max) da área desejada.
    
    Por padrão, restringe a atuação a uma pequena área (box_size_px, default 2cm x 2cm ≈ 80x80px)
    dentro da região indicada pelo usuário.
    """
    area_name = area_name.lower().strip()
    mid_x = screen_w // 2
    mid_y = screen_h // 2

    # Caso seja selecionado modo de quadrante inteiro ou "tela-toda"
    if full_quadrant or area_name in ("tela-toda", "tela_toda", "full"):
        quadrants = {
            "superior-esquerda": (padding, mid_x, padding, mid_y),
            "superior_esquerda": (padding, mid_x, padding, mid_y),
            "sup-esq": (padding, mid_x, padding, mid_y),
            "top-left": (padding, mid_x, padding, mid_y),

            "superior-direita": (mid_x, screen_w - padding, padding, mid_y),
            "superior_direita": (mid_x, screen_w - padding, padding, mid_y),
            "sup-dir": (mid_x, screen_w - padding, padding, mid_y),
            "top-right": (mid_x, screen_w - padding, padding, mid_y),

            "inferior-esquerda": (padding, mid_x, mid_y, screen_h - padding),
            "inferior_esquerda": (padding, mid_x, mid_y, screen_h - padding),
            "inf-esq": (padding, mid_x, mid_y, screen_h - padding),
            "bottom-left": (padding, mid_x, mid_y, screen_h - padding),

            "inferior-direita": (mid_x, screen_w - padding, mid_y, screen_h - padding),
            "inferior_direita": (mid_x, screen_w - padding, mid_y, screen_h - padding),
            "inf-dir": (mid_x, screen_w - padding, mid_y, screen_h - padding),
            "bottom-right": (mid_x, screen_w - padding, mid_y, screen_h - padding),

            "centro": (screen_w // 4, 3 * screen_w // 4, screen_h // 4, 3 * screen_h // 4),
            "center": (screen_w // 4, 3 * screen_w // 4, screen_h // 4, 3 * screen_h // 4),

            "tela-toda": (padding, screen_w - padding, padding, screen_h - padding),
            "tela_toda": (padding, screen_w - padding, padding, screen_h - padding),
            "full": (padding, screen_w - padding, padding, screen_h - padding),
        }
        if area_name in quadrants:
            return quadrants[area_name]

    # Modo padrão: Pequena caixa (ex: 2cm x 2cm ≈ 80x80px)
    half_box = box_size_px // 2

    areas = {
        # Centro (padrão)
        "centro": (mid_x - half_box, mid_x + half_box, mid_y - half_box, mid_y + half_box),
        "center": (mid_x - half_box, mid_x + half_box, mid_y - half_box, mid_y + half_box),

        # Superior Esquerda
        "superior-esquerda": (padding, padding + box_size_px, padding, padding + box_size_px),
        "superior_esquerda": (padding, padding + box_size_px, padding, padding + box_size_px),
        "sup-esq": (padding, padding + box_size_px, padding, padding + box_size_px),
        "top-left": (padding, padding + box_size_px, padding, padding + box_size_px),

        # Superior Direita
        "superior-direita": (screen_w - padding - box_size_px, screen_w - padding, padding, padding + box_size_px),
        "superior_direita": (screen_w - padding - box_size_px, screen_w - padding, padding, padding + box_size_px),
        "sup-dir": (screen_w - padding - box_size_px, screen_w - padding, padding, padding + box_size_px),
        "top-right": (screen_w - padding - box_size_px, screen_w - padding, padding, padding + box_size_px),

        # Inferior Esquerda
        "inferior-esquerda": (padding, padding + box_size_px, screen_h - padding - box_size_px, screen_h - padding),
        "inferior_esquerda": (padding, padding + box_size_px, screen_h - padding - box_size_px, screen_h - padding),
        "inf-esq": (padding, padding + box_size_px, screen_h - padding - box_size_px, screen_h - padding),
        "bottom-left": (padding, padding + box_size_px, screen_h - padding - box_size_px, screen_h - padding),

        # Inferior Direita
        "inferior-direita": (screen_w - padding - box_size_px, screen_w - padding, screen_h - padding - box_size_px, screen_h - padding),
        "inferior_direita": (screen_w - padding - box_size_px, screen_w - padding, screen_h - padding - box_size_px, screen_h - padding),
        "inf-dir": (screen_w - padding - box_size_px, screen_w - padding, screen_h - padding - box_size_px, screen_h - padding),
        "bottom-right": (screen_w - padding - box_size_px, screen_w - padding, screen_h - padding - box_size_px, screen_h - padding),
    }

    if area_name not in areas:
        opcoes_validas = [
            "superior-esquerda", "superior-direita",
            "inferior-esquerda", "inferior-direita",
            "centro", "tela-toda"
        ]
        raise ValueError(
            f"Área '{area_name}' inválida!\nOpções disponíveis: {', '.join(opcoes_validas)}"
        )

    return areas[area_name]


# ==============================================================================
# Execução Principal
# ==============================================================================

def log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Mantém o computador ativo simulando movimento e cliques periódicos do mouse em áreas pré-definidas."
    )
    parser.add_argument(
        "-a", "--area",
        type=str,
        default="centro",
        help="Área da tela. Opções: superior-esquerda, superior-direita, inferior-esquerda, inferior-direita, centro, tela-toda (padrão: centro)"
    )
    parser.add_argument(
        "--cm", "--size-cm",
        type=float,
        default=2.0,
        dest="size_cm",
        help="Tamanho do lado da área em centímetros (padrão: 2.0 cm)"
    )
    parser.add_argument(
        "--full-quadrant",
        action="store_true",
        help="Se ativado, utiliza o quadrante inteiro da tela em vez da pequena área de 2cm x 2cm."
    )
    parser.add_argument(
        "-m", "--move-interval",
        type=float,
        default=10.0,
        help="Intervalo em segundos (X) entre cada movimento do mouse (padrão: 10s)"
    )
    parser.add_argument(
        "-c", "--click-interval",
        type=float,
        default=30.0,
        help="Intervalo em segundos (Xy) entre cada clique do mouse (padrão: 30s). Defina como 0 para desativar cliques."
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.3,
        help="Duração do deslize suave do mouse em segundos (padrão: 0.3s)"
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    controller, engine_name = get_mouse_controller()
    screen_w, screen_h = controller.get_screen_size()

    box_size_px = cm_to_pixels(args.size_cm)

    try:
        x_min, x_max, y_min, y_max = get_area_bounds(
            area_name=args.area,
            screen_w=screen_w,
            screen_h=screen_h,
            box_size_px=box_size_px,
            full_quadrant=args.full_quadrant
        )
    except ValueError as err:
        print(f"\n[ERRO] {err}\n")
        sys.exit(1)

    print("=" * 65)
    print(" 🖱️  MOUSE KEEPER - COMPUTADOR ATIVO")
    print("=" * 65)
    print(f" • Motor de Controle:  {engine_name}")
    print(f" • Resolução da Tela:  {screen_w} x {screen_h}")
    if args.full_quadrant or args.area in ("tela-toda", "tela_toda", "full"):
        print(f" • Área Selecionada:   {args.area} (Modo Quadrante Amplo)")
    else:
        print(f" • Área Selecionada:   {args.area} (~{args.size_cm}cm x {args.size_cm}cm / {box_size_px}x{box_size_px}px)")
    print(f" • Delimitação Caixa:  X: {x_min} a {x_max} | Y: {y_min} a {y_max}")
    print(f" • Movimento a cada:   {args.move_interval} segundos (X)")
    if args.click_interval > 0:
        print(f" • Clique a cada:      {args.click_interval} segundos (Xy)")
    else:
        print(f" • Cliques:            Desativados")
    print("-" * 65)
    print(" ⌨️  Para interromper a qualquer momento: pressione Ctrl+C")
    if sys.platform == "darwin":
        print(" 🔒 No macOS, certifique-se de que seu Terminal possui permissão em:")
        print("    Ajustes do Sistema > Privacidade e Segurança > Acessibilidade")
    print("=" * 65 + "\n", flush=True)

    last_move_time = 0.0
    last_click_time = time.time()

    try:
        while True:
            now = time.time()

            # Momento de mover o mouse
            if now - last_move_time >= args.move_interval:
                target_x = random.randint(x_min, x_max)
                target_y = random.randint(y_min, y_max)
                log(f"Movendo mouse na área para ({target_x}, {target_y})")
                controller.move_to(target_x, target_y, duration=args.duration)
                last_move_time = time.time()

            # Momento de efetuar o clique
            if args.click_interval > 0 and (now - last_click_time >= args.click_interval):
                cur_x, cur_y = controller.get_position()
                log(f"👉 Efetuando clique em ({int(cur_x)}, {int(cur_y)})")
                controller.click()
                last_click_time = time.time()

            # Intervalo de checagem curto para resposta rápida ao Ctrl+C
            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n\n[INFO] Script finalizado com sucesso (Ctrl+C). Até logo!\n")


if __name__ == "__main__":
    main()
