from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.containers import Window, HSplit
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.formatted_text import FormattedText

from processors import MatchProcessor


def create_layout(finder):
    result_container = Window(
        BufferControl(
            buffer=finder.result_buffer,
            focusable=False,
            focus_on_click=True,
            include_default_input_processors=False,
            input_processors=[
                MatchProcessor(finder)
            ]
        ),
        height=D(min=1, max=finder.height),
        dont_extend_height=False,
        wrap_lines=False,
        always_hide_cursor=True,
        cursorline=True,
        get_line_prefix=finder.get_result_prefix,
    )

    status_container = Window(
        content=FormattedTextControl(finder.get_statusbar_text),
        height=D.exact(1),
        dont_extend_height=True,
        wrap_lines=False,
    )

    prompt_container = Window(
        BufferControl(
            buffer=finder.prompt_buffer,
            focusable=True,
            focus_on_click=True,
            include_default_input_processors=False,
        ),
        height=D.exact(1),
        dont_extend_height=True,
        wrap_lines=False,
        # TODO: use widget for styling instead?
        get_line_prefix=lambda _, __: FormattedText([("bold", "> ")]),
    )

    if finder.reverse:
        root_container = HSplit([
            prompt_container,
            status_container,
            result_container,
        ])
    else:
        root_container = HSplit([
            result_container,
            status_container,
            prompt_container,
        ])

    return Layout(root_container, focused_element=prompt_container)
