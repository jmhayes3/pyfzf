from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.filters import Condition
from prompt_toolkit.keys import Keys


def create_key_bindings(finder):
    key_bindings = KeyBindings()

    @Condition
    def is_multi():
        return finder.multi

    @key_bindings.add("escape")
    @key_bindings.add("c-c")
    @key_bindings.add("c-d")
    def exit_(event):
        event.app.exit()

    @key_bindings.add("up", eager=True)
    @key_bindings.add("c-p", eager=True)
    def cursor_up_(event):
        event.app.layout.get_buffer_by_name("result").cursor_up()

    @key_bindings.add("down", eager=True)
    @key_bindings.add("c-n", eager=True)
    def cursor_down_(event):
        event.app.layout.get_buffer_by_name("result").cursor_down()

    @key_bindings.add("tab", filter=is_multi)
    def select_(event):
        finder.selected_lines.add(
            event.app.layout.get_buffer_by_name("result").document.current_line
        )

    @key_bindings.add("s-tab", filter=is_multi)
    def unselect_(event):
        finder.selected_lines.discard(
            event.app.layout.get_buffer_by_name("result").document.current_line
        )

    # @key_bindings.add(Keys.ScrollUp)
    # def su_(event):
    #     finder.result_buffer.buffer.cursor_up()


    # @key_bindings.add(Keys.ScrollDown)
    # def sd_(event):
    #     finder.result_buffer.buffer.cursor_down()

    @key_bindings.add(Keys.Vt100MouseEvent)
    def mouse_event_(event):
        mouse_event = event.key_sequence[0].data
        if "[<0;" in mouse_event:
            # click
            pass
        elif "[<64;" in mouse_event:
            # scroll up
            event.app.layout.get_buffer_by_name("result").cursor_up()
        elif "[<65;" in mouse_event:
            # scroll down
            event.app.layout.get_buffer_by_name("result").cursor_down()

    return key_bindings
