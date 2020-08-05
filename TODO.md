* implement cache for storing input string and pattern combinations
* handle result buffer focus by processing "Keys.Any" key binding and check for WORD_CHARACTERS
  # Hide message when a key is pressed.
        def key_pressed(_):
            self.message = None
        self.application.key_processor.before_key_press += key_pressed

* implement highlighting of match positions

  class ReportingProcessor(Processor):
      """
      Highlight all pyflakes errors on the input.
      """
      def __init__(self, editor_buffer):
          self.editor_buffer = editor_buffer

      def apply_transformation(self, transformation_input):
          fragments = transformation_input.fragments

          if self.editor_buffer.report_errors:
              for error in self.editor_buffer.report_errors:
                  if error.lineno == transformation_input.lineno:
                      fragments = explode_text_fragments(fragments)
                      for i in range(error.start_column, error.end_column):
                          if i < len(fragments):
                              fragments[i] = ('class:flakeserror', fragments[i][1])

          return Transformation(fragments)

* fix not scrolling to top/bottom on scroll event when top/bottom content is visible in buffer
  ScrollOffsets()
* add tests
