"""Vim-style navigation mixins for the agentseq TUI.

Imports only from textual so it stays usable wherever DataTable / RichLog are.

- ``VimDataTable`` adds j/k/G/ctrl+d/ctrl+u and a ``gg`` sequence that move the
  row *cursor* (these tables use ``cursor_type="row"``).
- ``VimRichLog`` adds the same keys to scroll the transcript viewport.
"""
from __future__ import annotations

from textual.binding import Binding
from textual.events import Key
from textual.widgets import DataTable, RichLog


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(value, high))


class VimDataTable(DataTable):
    """A DataTable with vim-style row-cursor navigation.

    New action names are used so we never shadow DataTable's own
    ``action_cursor_up`` / ``action_cursor_down`` / page actions.
    """

    BINDINGS = [
        Binding("j", "vim_down", "Down", show=False),
        Binding("k", "vim_up", "Up", show=False),
        Binding("G", "vim_go_bottom", "Bottom", show=False),
        Binding("ctrl+d", "vim_half_down", "Half page down", show=False),
        Binding("ctrl+u", "vim_half_up", "Half page up", show=False),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._pending_g = False

    def action_vim_down(self) -> None:
        self.action_cursor_down()

    def action_vim_up(self) -> None:
        self.action_cursor_up()

    def action_vim_go_bottom(self) -> None:
        self.move_cursor(row=max(0, self.row_count - 1))

    def action_vim_half_down(self) -> None:
        if self.row_count == 0:
            return
        step = max(1, self.size.height // 2)
        cur = self.cursor_row or 0
        self.move_cursor(row=_clamp(cur + step, 0, max(0, self.row_count - 1)))

    def action_vim_half_up(self) -> None:
        if self.row_count == 0:
            return
        step = max(1, self.size.height // 2)
        cur = self.cursor_row or 0
        self.move_cursor(row=_clamp(cur - step, 0, max(0, self.row_count - 1)))

    def on_key(self, event: Key) -> None:
        if event.key == "g":
            if self._pending_g:
                self.move_cursor(row=0)
                self._pending_g = False
            else:
                self._pending_g = True
            event.stop()
        else:
            # Any other key cancels a pending ``g`` and is allowed to propagate
            # to bindings / ancestors.
            self._pending_g = False

    def on_blur(self) -> None:
        # Abandon a half-typed ``gg`` when focus leaves. Otherwise a stale
        # ``_pending_g`` survives focus changes that don't route a key through
        # this widget (a mouse click, a programmatic focus, or a priority
        # tab-switch binding that consumes the key first), and the next lone
        # ``g`` would spuriously jump to the top.
        self._pending_g = False


class VimRichLog(RichLog):
    """A RichLog with vim-style scrolling and a ``gg`` sequence."""

    # RichLog is already focusable in current textual; set it explicitly so
    # vim scrolling keeps working regardless of the installed version.
    can_focus = True

    BINDINGS = [
        Binding("j", "vim_down", "Down", show=False),
        Binding("k", "vim_up", "Up", show=False),
        Binding("G", "vim_bottom", "Bottom", show=False),
        Binding("ctrl+d", "vim_half_down", "Half page down", show=False),
        Binding("ctrl+u", "vim_half_up", "Half page up", show=False),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._pending_g = False

    def action_vim_down(self) -> None:
        self.scroll_down(animate=False)

    def action_vim_up(self) -> None:
        self.scroll_up(animate=False)

    def action_vim_bottom(self) -> None:
        self.scroll_end(animate=False)

    def action_vim_half_down(self) -> None:
        self.scroll_relative(y=max(1, self.size.height // 2), animate=False)

    def action_vim_half_up(self) -> None:
        self.scroll_relative(y=-max(1, self.size.height // 2), animate=False)

    def on_key(self, event: Key) -> None:
        if event.key == "g":
            if self._pending_g:
                self.scroll_home(animate=False)
                self._pending_g = False
            else:
                self._pending_g = True
            event.stop()
        else:
            self._pending_g = False

    def on_blur(self) -> None:
        # See VimDataTable.on_blur — drop a half-typed ``gg`` on focus loss.
        self._pending_g = False
