from prompt_toolkit.layout.processors import Processor, Transformation
from prompt_toolkit.layout.utils import explode_text_fragments


class MatchProcessor(Processor):
    """
    Input processor for highlighting all match positions.
    """
    def __init__(self, result_buffer):
        self.result_buffer = result_buffer

    def _transform_matches(self, match_positions, fragments):
        for mp in match_positions:
            fragments[mp] = ("fg:ansigreen", fragments[mp][1])
        return fragments

    def apply_transformation(self, transformation_input):
        fragments = transformation_input.fragments
        if self.result_buffer.relevant_lines:
            for line in self.result_buffer.relevant_lines:
                if line.line == fragments[0][1]:
                    fragments = explode_text_fragments(fragments)
                    fragments = self._transform_matches(
                        line.match_positions,
                        fragments
                    )
        return Transformation(fragments)
