import curses
import random
import time

PLAY_WIDTH = 60
PLAY_HEIGHT = 22
BOX_WIDTH = 5
BOX_SPRITE = "[###]"


def get_play_bounds(stdscr):
    """Calculate effective play area dimensions and centering offsets."""
    term_y, term_x = stdscr.getmaxyx()
    max_y = min(term_y, PLAY_HEIGHT)
    max_x = min(term_x, PLAY_WIDTH)
    offset_y = max(0, (term_y - max_y) // 2)
    offset_x = max(0, (term_x - max_x) // 2)
    return term_y, term_x, max_y, max_x, offset_y, offset_x


def safe_addstr(stdscr, y, x, string, attr=0, offset_y=0, offset_x=0):
    """Safely write string to curses window using relative play area coordinates."""
    term_y, term_x = stdscr.getmaxyx()
    abs_y = y + offset_y
    abs_x = x + offset_x

    if abs_y < 0 or abs_y >= term_y or abs_x >= term_x:
        return
    available_width = term_x - abs_x
    if available_width <= 0:
        return
    truncated_str = string[:available_width]

    try:
        if abs_y == term_y - 1 and abs_x + len(truncated_str) >= term_x:
            # Avoid write to absolute bottom-right corner which causes curses error
            if len(truncated_str) > 1:
                stdscr.addstr(abs_y, abs_x, truncated_str[:-1], attr)
                try:
                    stdscr.insch(abs_y, term_x - 1, ord(truncated_str[-1]), attr)
                except curses.error:
                    pass
        else:
            stdscr.addstr(abs_y, abs_x, truncated_str, attr)
    except curses.error:
        pass


def draw(stdscr, cannon_x, bullets, boxes, score, lives):
    """Render a single frame to stdscr, centered inside larger terminal windows."""
    stdscr.erase()
    term_y, term_x, max_y, max_x, offset_y, offset_x = get_play_bounds(stdscr)

    # Minimum terminal dimension check
    if term_y < 8 or term_x < 30:
        safe_addstr(stdscr, term_y // 2, max(0, (term_x - 18) // 2), "Terminal too small!")
        stdscr.refresh()
        return

    # Draw top and bottom borders (#) relative to play area
    safe_addstr(stdscr, 0, 0, "#" * max_x, 0, offset_y, offset_x)
    safe_addstr(stdscr, max_y - 1, 0, "#" * max_x, 0, offset_y, offset_x)

    # Draw left and right borders (#)
    for y in range(1, max_y - 1):
        safe_addstr(stdscr, y, 0, "#", 0, offset_y, offset_x)
        safe_addstr(stdscr, y, max_x - 1, "#", 0, offset_y, offset_x)

    # Draw HUD line at top
    hud_text = f"Score: {score}   Lives: {lives}   [Cannon Shooter]"
    safe_addstr(stdscr, 1, 2, hud_text, 0, offset_y, offset_x)

    # Draw active boxes [###]
    for box in boxes:
        safe_addstr(stdscr, box['y'], box['x'], BOX_SPRITE, 0, offset_y, offset_x)

    # Draw active bullets
    for b in bullets:
        safe_addstr(stdscr, b['y'], b['x'], "|", 0, offset_y, offset_x)

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
        safe_addstr(stdscr, start_y + i, clamped_x, line, 0, offset_y, offset_x)

    stdscr.refresh()


def show_game_over(stdscr, score):
    """Display centered game-over screen and wait for keypress."""
    stdscr.erase()
    term_y, term_x = stdscr.getmaxyx()

    msg1 = "GAME OVER"
    msg2 = f"Final Score: {score}"
    msg3 = "Press any key to exit"

    safe_addstr(stdscr, term_y // 2 - 2, max(0, (term_x - len(msg1)) // 2), msg1)
    safe_addstr(stdscr, term_y // 2, max(0, (term_x - len(msg2)) // 2), msg2)
    safe_addstr(stdscr, term_y // 2 + 2, max(0, (term_x - len(msg3)) // 2), msg3)

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

    term_y, term_x, max_y, max_x, offset_y, offset_x = get_play_bounds(stdscr)
    cannon_width = 5
    cannon_height = 3
    cannon_x = max(1, (max_x - cannon_width) // 2)
    bullets = []
    boxes = []

    score = 0
    lives = 3

    frame_count = 0
    base_spawn_interval = 45  # Initial spawn rate
    base_fall_interval = 12   # Initial fall rate
    max_boxes = 6

    # Input hold tracking & responsive movement
    last_left_press_time = 0.0
    last_right_press_time = 0.0
    HOLD_WINDOW = 0.15  # seconds
    MOVE_STEP = 1       # 1 cell per frame for smooth & faster movement

    target_frame_time = 1.0 / 30.0  # 30 FPS target

    while True:
        current_time = time.time()
        frame_count += 1

        # Read current screen dimensions and play bounds
        term_y, term_x, max_y, max_x, offset_y, offset_x = get_play_bounds(stdscr)
        max_cannon_x = max(1, max_x - 1 - cannon_width)
        cannon_x = max(1, min(cannon_x, max_cannon_x))

        # Dynamic difficulty scaling based on score
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
            elif ch in (ord(' '), 10, 13, curses.KEY_ENTER):
                fire_requested = True

        if should_quit:
            break

        # Process movement based on hold window (moves every frame when held for faster response)
        left_active = (current_time - last_left_press_time) < HOLD_WINDOW
        right_active = (current_time - last_right_press_time) < HOLD_WINDOW

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
            spawn_max_x = max(1, max_x - 1 - BOX_WIDTH)
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
                # Horizontal collision check (box is BOX_WIDTH wide)
                if box['x'] <= b['x'] < box['x'] + BOX_WIDTH:
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
