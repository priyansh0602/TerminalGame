# 🚀 Cannon Shooter

A fast-paced, keyboard-controlled ASCII arcade cannon shooter CLI game built for your terminal!

Defend your territory against falling ASCII blocks `[#]` by operating a ground cannon. As your score increases, the blocks fall faster and spawn more frequently.

---

## ⚡ Quick Start

```bash
pip install cannon-shooter
cannon-shoot
```

That's it — no cloning, no setup. (Windows users: `windows-curses` installs automatically as a dependency.)

---

## 🎮 Controls

| Key | Action |
| --- | --- |
| `A` / `Left Arrow` | Move Cannon Left |
| `D` / `Right Arrow` | Move Cannon Right |
| `Space` / `Enter` | Fire Bullet (`|`) |
| `Q` | Quit Game |

---

## ⚠️ Known Limitations

On some systems, firing (`Space`) may not register while a movement key is held simultaneously, due to a terminal input limitation. If this happens, use **Enter** as an alternate fire key, or tap A/D and Space separately rather than holding both at once.

---

## 🛠️ Installing from Source

If you want to clone the repository to inspect or modify the source code:

```bash
git clone https://github.com/priyansh0602/TerminalGame.git
cd TerminalGame
pip install .
```

Once installed, launch the game from any terminal:

```bash
cannon-shoot
```

---

## 🖥️ Recommended Terminals

For optimal rendering, smooth frame rates, and raw keyboard event handling, please run `cannon-shoot` in a dedicated terminal emulator:

- **Windows:** Windows Terminal (`wt.exe`), PowerShell, CMD
- **macOS:** Terminal.app, iTerm2
- **Linux:** GNOME Terminal, Alacritty, Kitty

*(Avoid running inside non-interactive IDE run-consoles or output panes as they may obscure raw keypresses.)*

---

## 🎯 Gameplay & Scoring

- **Scoring:** Destroying a falling box yields **+10 points**.
- **Lives:** You start with **3 lives**. A life is lost whenever a box reaches the bottom border of the screen.
- **Difficulty Scaling:** Every **75 points**, the difficulty increases:
  - Boxes fall faster (reduced frame interval down to minimum floor).
  - Boxes spawn more frequently.
- **Game Over:** When your lives reach 0, the game displays your final score and waits for a keypress before returning to your command prompt.
