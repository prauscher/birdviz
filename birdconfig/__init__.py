# -*- coding: utf-8 -*-

from .tokenizer import Tokenizer

def parse(stream):
    tokenizer = Tokenizer(stream)
    tokenizer.wordchars += ".:%/"
    return _parse_commands(tokenizer)

def _parse_arguments(tokenizer):
    args = []
    while True:
        token = tokenizer.safe_get()
        if token == ",":
            continue
        elif token == "{":
            args.append(_parse_scope(tokenizer))
            break
        elif token == "}":
            tokenizer.push_token(token)
            break
        elif token == ";":
            break
        else:
            if token.startswith('"') and token.endswith('"'):
                token = token[1:-1]
            args.append(token)
    return tuple(args)

def _parse_commands(tokenizer, end=None):
    parsed = dict()
    while True:
        try:
            command = tokenizer.safe_get()
        except EOFError:
            break
        if command == end:
            break

        if command not in parsed:
            parsed[command] = []
        parsed[command].append(_parse_arguments(tokenizer))

    return parsed

def _parse_scope(tokenizer):
    parsed = _parse_commands(tokenizer, "}")

    # Some scopes may end with };, some just with } - both is valid here
    next = tokenizer.get_token()
    if next != ";":
        tokenizer.push_token(next)

    return parsed
