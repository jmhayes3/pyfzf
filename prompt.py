from prompt_toolkit import prompt
from prompt_toolkit.styles import Style

from completer import FZFCompleter


def bottom_toolbar():
    return "toolbar"


def get_rprompt():
    return "rprompt"


style = Style.from_dict({
    "bottom-toolbar": "#ffffff bg:#333333",
    "rprompt": "#ffffff bg:#333333",
})

fzf_completer = FZFCompleter()
text = prompt("> ", vi_mode=True, completer=fzf_completer, complete_while_typing=True, complete_in_thread=True, bottom_toolbar=bottom_toolbar, rprompt=get_rprompt, style=style)
print(text)
