from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML


class FZFCompleter(Completer):
    def get_completions(self, document, complete_event):
        yield Completion("completion1", start_position=0, display=HTML("<b>completion1</b>"))
