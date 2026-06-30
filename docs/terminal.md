# Web Terminal

`/apps/terminal.html` uses xterm.js and a backend WebSocket at `/api/terminal/ws`.

## Security Considerations

- Terminal runs the shell configured by `TERMINAL_SHELL`.
- Deploy behind authentication and network controls.
- Restrict backend exposure in production.
