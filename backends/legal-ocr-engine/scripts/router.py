#!/usr/bin/env python3
"""Route OCR requests to the best available backend."""

class Router:
    def choose_backend(self, input_type, configured_backends):
        if 'paddle' in configured_backends and input_type in ('pdf', 'image'):
            return 'paddle'
        if 'mineru' in configured_backends:
            return 'mineru'
        return None
