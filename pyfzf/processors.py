from prompt_toolkit.layout.processors import Processor, Transformation
from prompt_toolkit.layout.utils import explode_text_fragments


class MatchProcessor(Processor):
    """
    Highlight all match positions.
    """
    def __init__(self, finder):
        self.finder = finder

    def apply_transformation(self, transformation_input):
        fragments = transformation_input.fragments
        for line in self.finder.matched_lines:
            if line[0] == fragments[0][1]:
                fragments = explode_text_fragments(fragments)
                for i, fragment in enumerate(fragments):
                    if i in line[2]:
                        fragments[i] = ("ansigreen", fragments[i][1])
        return Transformation(fragments)
