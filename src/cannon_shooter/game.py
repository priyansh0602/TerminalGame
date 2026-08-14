import curses
import random
import time


def safe_addstr(stdscr, y, x, string, attr=0):
    """Safely write string to curses window without crashing on screen boundaries."""
    max_y, max_x = stdscr.getmaxyx()
    if y < 0 or y >= max_y or x >= max_x:
        return
    available_width = max_x - x
    if available_width <= 0:
        return
    truncated_str = string[:available_width]

    try:
        if y == max_y - 1 and x + len(truncated_str) >= max_x:
            # Avoid write to absolute bottom-right corner which causes curses error
            if len(truncated_str) > 1:
                stdscr.addstr(y, x, truncated_str[:-1], attr)
                try:
                    stdscr.insch(y, max_x - 1, ord(truncated_str[-1]), attr)
                except curses.error:
                    pass
        else:
            stdscr.addstr(y, x, truncated_str, attr)
    except curses.error:
        pass


def draw(stdscr, cannon_x, bullets, boxes, score, lives):
    """Render a single frame to stdscr."""
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()

    # Minimum terminal dimension check
    if max_y < 8 or max_x < 30:
        safe_addstr(stdscr, max_y // 2, max(0, (max_x - 18) // 2), "Terminal too small!")
        stdscr.refresh()
        return

    # Draw top and bottom borders (#)
    safe_addstr(stdscr, 0, 0, "#" * max_x)
    safe_addstr(stdscr, max_y - 1, 0, "#" * max_x)

    # Draw left and right borders (#)
    for y in range(1, max_y - 1):
        safe_addstr(stdscr, y, 0, "#")
        safe_addstr(stdscr, y, max_x - 1, "#")

    # Draw HUD line at top
    hud_text = f"Score: {score}   Lives: {lives}   [Cannon Shooter]"
    safe_addstr(stdscr, 1, 2, hud_text)

    # Draw active boxes [#]
    for box in boxes:
        safe_addstr(stdscr, box['y'], box['x'], "[#]")

    # Draw active bullets
    for b in bullets:
        safe_addstr(stdscr, b['y'], b['x'], "|")

    # ASCII Cannon art (width = 5, height = 3)
    cannon_art = [
        "  |  ",
        " /^\\ ",
        "[===]"
    ]
    cannon_width = 5
    cannon_height = len(cannon_art)

    # Position cannon resting above bottom border
    start_y = max_y - 1 - cannon_height
    clamped_x = max(1, min(cannon_x, max_x - 1 - cannon_width))

    for i, line in enumerate(cannon_art):
        safe_addstr(stdscr, start_y + i, clamped_x, line)

    stdscr.refresh()


def show_game_over(stdscr, score):
    """Display centered game-over screen and wait for keypress."""
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()

    msg1 = "GAME OVER"
    msg2 = f"Final Score: {score}"
    msg3 = "Press any key to exit"

    safe_addstr(stdscr, max_y // 2 - 2, max(0, (max_x - len(msg1)) // 2), msg1)
    safe_addstr(stdscr, max_y // 2, max(0, (max_x - len(msg2)) // 2), msg2)
    safe_addstr(stdscr, max_y // 2 + 2, max(0, (max_x - len(msg3)) // 2), msg3)

    stdscr.refresh()
    stdscr.nodelay(False)  # Blocking input mode
    try:
        stdscr.getch()
    except curses.error:
        pass


def main(stdscr):
    """Main curses event & render loop."""
    try:
        curses.curs_set(0)  # Hide cursor if supported
    except curses.error:
        pass

    stdscr.nodelay(True)  # Truly non-blocking getch

    max_y, max_x = stdscr.getmaxyx()
    cannon_width = 5
    cannon_height = 3
    cannon_x = max(1, (max_x - cannon_width) // 2)
    bullets = []
    boxes = []

    score = 0
    lives = 3
    box_width = 3

    frame_count = 0
    base_spawn_interval = 35  # Slower initial spawn rate (Fix 1)
    base_fall_interval = 6   # Slower initial fall rate (Fix 1)
    max_boxes = 6

    # Input hold tracking & throttled movement (Fix 2)
    last_left_press_time = 0.0
    last_right_press_time = 0.0
    HOLD_WINDOW = 0.15  # seconds
    MOVE_STEP = 1       # 1 cell per movement (Fix 2)
    MOVE_THROTTLE = 2   # Move every 2nd frame while held (Fix 2)

    target_frame_time = 1.0 / 30.0  # 30 FPS target

    while True:
        current_time = time.time()
        frame_count += 1

        # Read current screen dimensions
        max_y, max_x = stdscr.getmaxyx()
        max_cannon_x = max(1, max_x - 1 - cannon_width)
        cannon_x = max(1, min(cannon_x, max_cannon_x))

        # Dynamic difficulty scaling based on score (more gradual ramp: 75 pts per level) (Fix 1)
        level = score // 75
        fall_interval = max(1, base_fall_interval - level)
        spawn_interval = max(10, base_spawn_interval - level * 3)

        # Drain input queue
        should_quit = False
        fire_requested = False

        while True:
            try:
                ch = stdscr.getch()
            except curses.error:
                ch = -1

            if ch == -1:
                break

            if ch in (ord('q'), ord('Q')):
                should_quit = True
                break
            elif ch in (ord('a'), ord('A'), curses.KEY_LEFT):
                last_left_press_time = current_time
            elif ch in (ord('d'), ord('D'), curses.KEY_RIGHT):
                last_right_press_time = current_time
            elif ch == ord(' '):
                fire_requested = True

        if should_quit:
            break

        # Process movement based on hold window and per-frame throttle (Fix 2)
        left_active = (current_time - last_left_press_time) < HOLD_WINDOW
        right_active = (current_time - last_right_press_time) < HOLD_WINDOW

        if frame_count % MOVE_THROTTLE == 0:
            if left_active and not right_active:
                cannon_x = max(1, cannon_x - MOVE_STEP)
            elif right_active and not left_active:
                cannon_x = min(max_cannon_x, cannon_x + MOVE_STEP)

        # Process firing
        if fire_requested:
            cannon_tip_x = cannon_x + 2
            cannon_top_y = max_y - 1 - cannon_height
            bullet_start_y = cannon_top_y - 1
            if bullet_start_y > 0:
                bullets.append({'x': cannon_tip_x, 'y': bullet_start_y})

        # Update bullets position
        new_bullets = []
        for b in bullets:
            b['y'] -= 1
            if b['y'] > 0:  # Keep bullets until they hit top border
                new_bullets.append(b)
        bullets = new_bullets

        # Spawn box
        if frame_count % spawn_interval == 0 and len(boxes) < max_boxes:
            spawn_max_x = max(1, max_x - 1 - box_width)
            if spawn_max_x >= 1:
                spawn_x = random.randint(1, spawn_max_x)
                boxes.append({'x': spawn_x, 'y': 2})

        # Update boxes position
        if frame_count % fall_interval == 0:
            retained_boxes = []
            for box in boxes:
                box['y'] += 1
                if box['y'] >= max_y - 1:  # Reached bottom border
                    lives -= 1
                else:
                    retained_boxes.append(box)
            boxes = retained_boxes

        # Collision detection (Bullets vs Boxes)
        bullets_to_remove = set()
        boxes_to_remove = set()

        for b_idx, b in enumerate(bullets):
            for box_idx, box in enumerate(boxes):
                if box_idx in boxes_to_remove:
                    continue
                # Horizontal collision check (box is 3 wide: [x, x+1, x+2])
                if box['x'] <= b['x'] < box['x'] + box_width:
                    # Vertical collision tolerance (within 1 row)
                    if abs(b['y'] - box['y']) <= 1:
                        bullets_to_remove.add(b_idx)
                        boxes_to_remove.add(box_idx)
                        score += 10
                        break

        bullets = [b for idx, b in enumerate(bullets) if idx not in bullets_to_remove]
        boxes = [box for idx, box in enumerate(boxes) if idx not in boxes_to_remove]

        # Check for Game Over condition
        if lives <= 0:
            show_game_over(stdscr, score)
            break

        # Render frame
        draw(stdscr, cannon_x, bullets, boxes, score, lives)

        # Frame rate cap (~30 FPS)
        elapsed = time.time() - current_time
        sleep_time = target_frame_time - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

    return score


def run():
    """Entry point for cannon-shoot command."""
    final_score = curses.wrapper(main)
    if final_score is not None:
        print(f"Game Over! Final Score: {final_score}")


if __name__ == "__main__":
    run()
