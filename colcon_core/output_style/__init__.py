# Copyright 2024 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

import os
from types import SimpleNamespace

from colcon_core.environment_variable import EnvironmentVariable
from colcon_core.plugin_system import get_first_line_doc
from colcon_core.plugin_system import instantiate_extensions
from colcon_core.plugin_system import order_extensions_grouped_by_priority

"""Environment variable to override the default output style"""
DEFAULT_OUTPUT_STYLE_ENVIRONMENT_VARIABLE = EnvironmentVariable(
    'COLCON_DEFAULT_OUTPUT_STYLE', 'Select the default output style extension')


class Stylizer:
    """A text style modifier."""

    __slots__ = ('start', 'end')

    def __init__(self, start=None, end=None):  # noqa: D107
        self.start = start or ''
        self.end = end or ''

    def __add__(self, other):
        """Combine two modifiers into a single modifier."""
        if not isinstance(other, Stylizer):
            raise TypeError()
        return Stylizer(
            self.start + other.start,
            other.end + self.end)

    def __call__(self, text):
        """
        Apply style modification to the given text.

        :param text: Text to be modified
        :returns: Modified text
        """
        return self.start + text + self.end


Style = SimpleNamespace(
    Critical=Stylizer('', ''),
    Default=Stylizer('', ''),
    Error=Stylizer('', ''),
    PackageOrJobName=Stylizer('', ''),
    SectionEnd=Stylizer('', ''),
    SectionStart=Stylizer('', ''),
    Strong=Stylizer('', ''),
    Success=Stylizer('', ''),
    Warning=Stylizer('', ''),
    Weak=Stylizer('', ''),
)


class OutputStyleExtensionPoint:
    """The interface for stylizing colcon output."""

    """The version of the output style extension interface."""
    EXTENSION_POINT_VERSION = '1.0'

    """The default priority of output style extensions."""
    PRIORITY = 100

    def __init__(self):  # noqa: D107
        super().__init__()

    def apply_style(self, style):
        """
        Apply output style modifications.

        :param style: The current output style
        """
        pass


def get_output_style_extensions(*, group_name=None):
    """
    Get the available output style extensions.

    The extensions are grouped by their priority and each group is ordered by
    the entry point name.

    :rtype: OrderedDict
    """
    if group_name is None:
        group_name = __name__
    extensions = instantiate_extensions(group_name)
    return order_extensions_grouped_by_priority(extensions)


def add_output_style_arguments(parser, *, extensions=None):
    """
    Add the command line arguments for the output style extensions.

    :param parser: The argument parser
    :param extensions: The output style extensions to use, if `None` is passed
      use the extensions provided by
      :function:`get_output_style_extensions`
    """
    if extensions is None:
        extensions = get_output_style_extensions()
    group = parser.add_argument_group(title='Output style arguments')
    keys = []
    descriptions = ''
    for priority in extensions.keys():
        extensions_same_prio = extensions[priority]
        assert len(extensions_same_prio) == 1, \
            'Output style extensions must have unique priorities'
        for key, extension in extensions_same_prio.items():
            keys.append(key)
            desc = get_first_line_doc(extension)
            if not desc:
                # show extensions without a description
                # to mention the available options
                desc = '<no description>'
            # it requires a custom formatter to maintain the newline
            descriptions += f'\n* {key}: {desc}'

    if not keys:
        return

    default = os.environ.get(DEFAULT_OUTPUT_STYLE_ENVIRONMENT_VARIABLE.name)
    if default not in keys:
        default = keys[0]

    group.add_argument(
        '--output-style', type=str, choices=keys, default=default,
        help='The style extension to use when producing output '
             f'(default: {default}){descriptions}')  # noqa: E131


def select_output_style_extension(args, *, extensions=None):
    """
    Get the output style extension.

    :param args: The parsed command line arguments
    :param extensions: The output style extensions to use, if `None` is passed
      use the extensions provided by
      :function:`get_output_style_extensions`

    :returns: The output style extension (or None if not available)
    """
    if extensions is None:
        extensions = get_output_style_extensions()
    for priority in extensions.keys():
        extensions_same_prio = extensions[priority]
        for key, extension in extensions_same_prio.items():
            if key == args.output_style:
                return extension


def apply_output_style(args, *, extensions=None):
    """
    Apply output style for the appropriate extension if any are available.

    :param args: The parsed command line arguments
    :param extensions: The output style extensions to use, if `None` is passed
      use the extensions provided by
      :function:`get_output_style_extensions`
    """
    # TODO: This approach chooses only a single extension. Should it be
    #       possible to apply styles on top of each other, possibly ones which
    #       serve different purposes?
    #       Expressing styles similar to event handlers might be the only way
    #       to expose that on the command line.
    extension = select_output_style_extension(args, extensions=extensions)
    if extension is not None:
        extension.apply_style(Style)