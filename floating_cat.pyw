"""
Floating Cat Desktop Companion (플로팅 데스크톱 펫)
- assets/NEW 디렉토리의 신규 스프라이트 애니메이션 완벽 연동:
  * NEW/walk: 10프레임 자연스러운 보행 사이클 (walk_01 ~ walk_10)
  * NEW/grooming: 10프레임 귀여운 그루밍 사이클 (grooming_01 ~ grooming_10)
  * NEW/scruff_hold: 1프레임 뒷덜미 잡힘 (scruff_hold_01)
- 진행 방향 일치 (기본 좌측 이동, 우측 이동 시 FLIP_LEFT_RIGHT 자동 반전, 문워크 완벽 차단)
- 흔들림/지터링 제로: 균일 규격(Uniform Canvas) & 고정 접지선(Ground Anchor)
- 마우스 드래그 시 커서 위치와 손(뒷덜미) 앵커 정확히 일치 & 진자 흔들림 물리
- 우클릭 시 종료
"""

import os
import sys
import math
import random
import tkinter as tk
from PIL import Image, ImageTk

# Base directory & Assets directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NEW_ASSETS_DIR = os.path.join(BASE_DIR, "assets", "NEW")
WALK_DIR = os.path.join(NEW_ASSETS_DIR, "walk")
GROOM_DIR = os.path.join(NEW_ASSETS_DIR, "grooming")
SCRUFF_DIR = os.path.join(NEW_ASSETS_DIR, "scruff_hold")

# Chroma Key Color for Windows Transparent Window
CHROMA_KEY_HEX = "#000001"
CHROMA_KEY_RGB = (0, 0, 1)

class FloatingCatApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Floating Cat")
        
        # Window attributes for borderless transparent topmost overlay
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-transparentcolor", CHROMA_KEY_HEX)
        self.root.config(bg=CHROMA_KEY_HEX)

        # Screen dimensions
        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()
        
        # Window size & canvas setup (280x280 for ample swing space)
        self.win_size = 280
        self.pivot_x = 140
        self.pivot_y = 60
        
        self.canvas = tk.Canvas(
            self.root,
            width=self.win_size,
            height=self.win_size,
            bg=CHROMA_KEY_HEX,
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill="both", expand=True)

        # Ground level (just above taskbar, ~60px from screen bottom)
        self.ground_y = self.screen_h - self.win_size - 60
        
        # Position and physics state
        self.x = random.randint(100, max(200, self.screen_w - 350))
        self.y = self.ground_y
        self.vx = 0.0
        self.vy = 0.0
        
        # Load sprites from assets/NEW
        self.load_sprites()
        
        # Walk & Groom state machine
        # States: 'WALK', 'GROOM', 'HELD', 'FALLING'
        self.state = 'WALK'
        self.direction = random.choice([1, -1]) # 1: Moving Right, -1: Moving Left
        self.walk_speed = 1.35
        self.state_timer = 0
        self.next_state_ticks = self.random_walk_duration()
        
        # Animation frame counter
        self.anim_tick = 0
        
        # Scruff Drag & Inertia Swing Physics
        self.is_held = False
        self.prev_mouse_x = 0
        self.prev_mouse_y = 0
        self.mouse_vx = 0.0
        self.mouse_vy = 0.0
        
        # Pendulum Angle Physics (in degrees)
        self.angle = 0.0
        self.angle_vel = 0.0
        self.target_angle = 0.0
        
        # Event Bindings
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.on_right_click)

        # Position window initially
        self.update_window_position()

        # Start game loop (~40 FPS, 25ms per tick)
        self.tick_ms = 25
        self.root.after(self.tick_ms, self.update_loop)

    def load_sprites(self):
        """Load NEW assets for walk, grooming, and scruff_hold"""
        # 1. Walk frames (10 frames: walk_01.png .. walk_10.png)
        # Note: Original sprites naturally face LEFT
        walk_files = sorted([f for f in os.listdir(WALK_DIR) if f.endswith(".png")])
        self.walk_frames_left = []
        self.walk_frames_right = []
        for f in walk_files:
            im = Image.open(os.path.join(WALK_DIR, f)).convert("RGBA")
            self.walk_frames_left.append(im)
            self.walk_frames_right.append(im.transpose(Image.FLIP_LEFT_RIGHT))

        # 2. Grooming frames (10 frames: grooming_01.png .. grooming_10.png)
        groom_files = sorted([f for f in os.listdir(GROOM_DIR) if f.endswith(".png")])
        self.groom_frames_left = []
        self.groom_frames_right = []
        for f in groom_files:
            im = Image.open(os.path.join(GROOM_DIR, f)).convert("RGBA")
            self.groom_frames_left.append(im)
            self.groom_frames_right.append(im.transpose(Image.FLIP_LEFT_RIGHT))

        # 3. Scruff / Grabbed frame (scruff_hold_01.png)
        scruff_path = os.path.join(SCRUFF_DIR, "scruff_hold_01.png")
        scruff_im = Image.open(scruff_path).convert("RGBA")
        
        # Center the hand pinch point (x=105, y=6) precisely at (pivot_x, pivot_y)
        self.scruff_base = Image.new("RGBA", (self.win_size, self.win_size), (0, 0, 0, 0))
        paste_x = self.pivot_x - 105
        paste_y = self.pivot_y - 6
        self.scruff_base.paste(scruff_im, (paste_x, paste_y), mask=scruff_im)

    def random_walk_duration(self):
        """Walk duration: 2 to 8 seconds in ticks (40 ticks/sec)"""
        return int(random.uniform(2.0, 8.0) * (1000 / 25))

    def random_groom_duration(self):
        """Groom duration: 10 to 40 seconds in ticks (40 ticks/sec)"""
        return int(random.uniform(10.0, 40.0) * (1000 / 25))

    def composite_image(self, pil_rgba):
        """Composite RGBA PIL image onto chroma key for transparent display"""
        base = Image.new("RGB", pil_rgba.size, CHROMA_KEY_RGB)
        base.paste(pil_rgba, mask=pil_rgba.split()[3])
        return ImageTk.PhotoImage(base)

    def update_window_position(self):
        """Update Tkinter window position on screen"""
        self.root.geometry(f"{self.win_size}x{self.win_size}+{int(self.x)}+{int(self.y)}")

    # ═════════════════════════════════════════════════════════════
    # MOUSE EVENT HANDLERS (뒷덜미 잡기 & 드래그)
    # ═════════════════════════════════════════════════════════════
    def on_press(self, event):
        """User clicks cat: Pick up by the scruff!"""
        self.is_held = True
        self.state = 'HELD'
        self.prev_mouse_x = event.x_root
        self.prev_mouse_y = event.y_root
        self.mouse_vx = 0.0
        self.mouse_vy = 0.0
        self.angle_vel = 0.0
        
        # Center the hand pinch point precisely on mouse cursor
        self.x = event.x_root - self.pivot_x
        self.y = event.y_root - self.pivot_y
        self.update_window_position()

    def on_drag(self, event):
        """User moves mouse while holding: Follow mouse with inertia velocity"""
        if not self.is_held:
            return
        
        # Track velocity from mouse delta
        dx = event.x_root - self.prev_mouse_x
        dy = event.y_root - self.prev_mouse_y
        self.prev_mouse_x = event.x_root
        self.prev_mouse_y = event.y_root
        
        # Smooth mouse velocity
        self.mouse_vx = self.mouse_vx * 0.35 + dx * 0.65
        self.mouse_vy = self.mouse_vy * 0.35 + dy * 0.65
        
        # Target tilt angle based on acceleration/movement
        self.target_angle = -max(-38.0, min(38.0, self.mouse_vx * 2.0))
        
        # Follow cursor
        self.x = event.x_root - self.pivot_x
        self.y = event.y_root - self.pivot_y
        self.update_window_position()

    def on_release(self, event):
        """User releases mouse: Fall down to ground if mid-air"""
        if not self.is_held:
            return
        self.is_held = False
        
        self.vx = max(-12.0, min(12.0, self.mouse_vx * 0.55))
        self.vy = max(-10.0, min(10.0, self.mouse_vy * 0.55))
        
        if self.y < self.ground_y:
            self.state = 'FALLING'
        else:
            self.y = self.ground_y
            self.state = 'WALK'
            self.state_timer = 0
            self.next_state_ticks = self.random_walk_duration()

    def on_right_click(self, event):
        """Right click: Close application"""
        self.root.destroy()
        sys.exit(0)

    # ═════════════════════════════════════════════════════════════
    # MAIN UPDATE LOOP
    # ═════════════════════════════════════════════════════════════
    def update_loop(self):
        self.anim_tick += 1
        
        if self.state == 'HELD':
            self.update_held()
        elif self.state == 'FALLING':
            self.update_falling()
        elif self.state == 'WALK':
            self.update_walk()
        elif self.state == 'GROOM':
            self.update_groom()
            
        self.update_window_position()
        self.root.after(self.tick_ms, self.update_loop)

    def update_held(self):
        """Physics when held by scruff: Damped pendulum oscillation"""
        self.mouse_vx *= 0.72
        self.mouse_vy *= 0.72
        
        target = self.target_angle * 0.82
        self.target_angle *= 0.85
        
        # Spring-damper pendulum physics
        spring_k = 0.085   # Restoring spring force towards gravity
        damping = 0.92     # Air resistance friction
        
        accel = -spring_k * (self.angle - target)
        self.angle_vel = (self.angle_vel + accel) * damping
        self.angle += self.angle_vel
        
        # Rotate around the hand pivot (pivot_x, pivot_y)
        rot_img = self.scruff_base.rotate(
            self.angle,
            resample=Image.Resampling.BICUBIC,
            center=(self.pivot_x, self.pivot_y)
        )
        self.current_photo = self.composite_image(rot_img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.current_photo)

    def update_falling(self):
        """Gravity and landing physics when released in mid-air"""
        self.vy += 0.88
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.98
        
        accel = -0.065 * self.angle
        self.angle_vel = (self.angle_vel + accel) * 0.93
        self.angle += self.angle_vel
        
        if self.y >= self.ground_y:
            self.y = self.ground_y
            self.vy = 0
            self.vx = 0
            self.angle = 0
            self.angle_vel = 0
            self.state = 'WALK'
            self.state_timer = 0
            self.next_state_ticks = self.random_walk_duration()
            return
            
        if self.x < 0:
            self.x = 0
            self.vx = abs(self.vx) * 0.5
        elif self.x > self.screen_w - self.win_size:
            self.x = self.screen_w - self.win_size
            self.vx = -abs(self.vx) * 0.5
            
        rot_img = self.scruff_base.rotate(
            self.angle,
            resample=Image.Resampling.BICUBIC,
            center=(self.pivot_x, self.pivot_y)
        )
        self.current_photo = self.composite_image(rot_img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.current_photo)

    def update_walk(self):
        """Walk state: 10-frame smooth walk cycle from NEW/walk"""
        self.state_timer += 1
        
        # Move horizontally
        self.x += self.direction * self.walk_speed
        
        # Screen edge bounce
        margin = 15
        if self.x <= margin:
            self.x = margin
            self.direction = 1  # Face right & move right
        elif self.x >= self.screen_w - self.win_size - margin:
            self.x = self.screen_w - self.win_size - margin
            self.direction = -1 # Face left & move left
            
        # 10-frame smooth walk cycle: advance every 4 ticks (100ms per frame)
        num_frames = len(self.walk_frames_left)
        frame_idx = (self.anim_tick // 4) % num_frames
        
        # Natural left facing: direction == -1
        # Flipped right facing: direction == 1
        frames = self.walk_frames_right if self.direction == 1 else self.walk_frames_left
        raw_frame = frames[frame_idx]

        # Fixed canvas & ground anchor
        canvas_img = Image.new("RGBA", (self.win_size, self.win_size), (0, 0, 0, 0))
        pos_x = (self.win_size - raw_frame.width) // 2
        pos_y = self.win_size - raw_frame.height - 15
        canvas_img.paste(raw_frame, (pos_x, pos_y), mask=raw_frame)
        
        self.current_photo = self.composite_image(canvas_img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.current_photo)
        
        # Transition to GROOM
        if self.state_timer >= self.next_state_ticks:
            self.state = 'GROOM'
            self.state_timer = 0
            self.next_state_ticks = self.random_groom_duration()

    def update_groom(self):
        """Groom state: 10-frame grooming cycle from NEW/grooming"""
        self.state_timer += 1
        
        # 10-frame grooming cycle: advance every 4 ticks (~100ms per frame)
        num_frames = len(self.groom_frames_left)
        frame_idx = (self.anim_tick // 4) % num_frames
        
        # Face same direction as the last walk
        frames = self.groom_frames_right if self.direction == 1 else self.groom_frames_left
        raw_frame = frames[frame_idx]
        
        # Fixed canvas & ground anchor
        canvas_img = Image.new("RGBA", (self.win_size, self.win_size), (0, 0, 0, 0))
        pos_x = (self.win_size - raw_frame.width) // 2
        pos_y = self.win_size - raw_frame.height - 15
        canvas_img.paste(raw_frame, (pos_x, pos_y), mask=raw_frame)
        
        self.current_photo = self.composite_image(canvas_img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.current_photo)
        
        # Transition to WALK
        if self.state_timer >= self.next_state_ticks:
            self.state = 'WALK'
            self.state_timer = 0
            self.next_state_ticks = self.random_walk_duration()
            if random.random() < 0.5:
                self.direction *= -1

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = FloatingCatApp()
    app.run()
