# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from io import StringIO
import os

from colcon_core.logging import colcon_logger
try:
    from em import Configuration
    from em import Interpreter
except ImportError as e:
    try:
        import em  # noqa: F401
    except ImportError:
        e.msg += " The Python package 'empy' must be installed"
        raise e from None
    e.msg += " The Python package 'empy' must be installed and 'em' must " \
        'not be installed since both packages share the same namespace'
    raise e from None

logger = colcon_logger.getChild(__name__)


def expand_template(template_path, destination_path, data):
    """
    Expand an EmPy template.

    The directory of the destination path is created if necessary.

    :param template_path: The patch of the template file
    :param destination_path: The path of the generated expanded file
    :param dict data: The data used for expanding the template
    :raises: Any exception which `em.Interpreter.string` might raise
    """
    output = StringIO()
    interpreter = None
    try:
        config = Configuration(
            defaultRoot=str(template_path),
            defaultStdout=output,
            useProxy=False)
        interpreter = CachingInterpreter(config=config, dispatcher=False)
        with template_path.open('r') as h:
            content = h.read()
        interpreter.string(content, locals=data)
        output = output.getvalue()
    except Exception as e:  # noqa: F841
        logger.error(
            f"{e.__class__.__name__} processing template '{template_path}'")
        raise
    else:
        os.makedirs(str(destination_path.parent), exist_ok=True)
        # if the destination_path is a symlink remove the symlink
        # to avoid writing to the symlink destination
        if destination_path.is_symlink():
            destination_path.unlink()
        with destination_path.open('w') as h:
            h.write(output)
    finally:
        if interpreter is not None:
            interpreter.shutdown()


cached_tokens = {}


class CachingInterpreter(Interpreter):
    """Interpreter for EmPy which which caches parsed tokens."""

    def parse(self, scanner, locals=None):  # noqa: A002 D102
        global cached_tokens
        data = scanner.buffer
        # try to use cached tokens
        tokens = cached_tokens.get(data)
        if tokens is None:
            # collect tokens and cache them
            tokens = []
            while True:
                token = scanner.one()
                if token is None:
                    break
                tokens.append(token)
            cached_tokens[data] = tokens

        # reimplement the parse method using the (cached) tokens
        self.invoke('atParse', scanner=scanner, locals=locals)
        for token in tokens:
            self.invoke('atToken', token=token)
            self.run(token, locals)
            scanner.accumulate()
        return True
