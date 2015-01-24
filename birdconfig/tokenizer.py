# -*- coding: utf-8 -*-

import shlex

class Tokenizer(shlex.shlex):
    def safe_get(self):
        token = self.get_token()
        if not token:
            raise EOFError()
        return token
