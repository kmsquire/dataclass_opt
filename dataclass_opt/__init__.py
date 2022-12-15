"""A library for building ArgumentParsers from dataclasses.
"""

import argparse
import re
import sys
import typing
from argparse import *  # noqa: F401, F403
from argparse import ArgumentParser, Namespace
from collections.abc import Mapping
from dataclasses import MISSING, field, fields, is_dataclass, make_dataclass

from inflection import dasherize, underscore

if sys.version_info >= (3, 9, 0):
    from argparse import BooleanOptionalAction


__version__ = "0.1.0"


class MustBeADataclass(Exception):
    pass


class NoDefaultFunction(Exception):
    pass


class UnsupportedException(Exception):
    pass


def _is_arg(dc_field):
    return "_names" not in dc_field.metadata


def _get_names(dc_field):
    """Return the short and long option names for a field."""
    metadata = dc_field.metadata

    if "_names" not in metadata:
        # This is an argument, not an option
        yield dc_field.name

    else:
        names = metadata["_names"]

        if names:
            for name in names:
                yield name

            long = metadata.get("long", MISSING)
            if long != MISSING and long:
                yield long

            short = metadata.get("short", MISSING)
            if short != MISSING and short:
                yield short
        else:
            long = metadata.get("long", MISSING)
            if long != MISSING and long:
                yield long
            elif long == MISSING:
                yield "--" + dc_field.name.replace("_", "-")

            short = metadata.get("short", MISSING)
            if short != MISSING and short:
                yield short
            elif short == MISSING:
                for match in re.finditer(r"\w", dc_field.name):
                    yield "-" + match.group(0)
                    break


def _get_type(arg_type):
    base_type = None
    is_optional = False
    is_list = False

    if (
        isinstance(arg_type, typing._GenericAlias)
        or sys.version_info >= (3, 9, 0)
        and isinstance(arg_type, typing.GenericAlias)
    ):
        origin = arg_type.__origin__
        args = arg_type.__args__

        # Check if type is Optional, and unwrap if needed
        # Note: Optional is an alias for Union[type, None]
        if origin == typing.Union:
            if type(None) in args:
                is_optional = True
                if len(args) == 2:
                    base_type, _, is_list = _get_type(args[0])
                else:
                    # This is still a Union, even after removing "Optional", so punt on the type
                    pass
            else:
                # This is a normal Union; punt on the type
                pass
        elif origin == list or arg_type._name == "List":
            is_list = True
            if len(args) == 1:
                parm_base_type, _, parm_is_list = _get_type(args[0])
                if not parm_is_list:
                    base_type = parm_base_type
            else:
                # Not sure what to do here
                pass
        else:
            # Type is not a List or Union, so punt on the type
            pass

    else:
        base_type = arg_type

    if isinstance(base_type, typing._Final):
        base_type = None

    return base_type, is_optional, is_list


def _get_action(is_arg, arg_type):
    if not is_arg and arg_type == bool:
        return "store_true"

    return None


def _to_name_command_dict(commands):
    if is_dataclass(commands):
        command = commands
        name = command.__name__
        return {dasherize(underscore(name)): command}

    if isinstance(commands, Mapping):
        return commands

    if isinstance(commands, list):
        return {dasherize(underscore(command.__name__)): command for command in commands}


def opt(*names, **kwargs):
    default = kwargs.pop("default", MISSING)
    if default == argparse.SUPPRESS:
        raise UnsupportedException("SUPPRESS is unsupported in dataclass_opt")
    default_factory = kwargs.pop("default_factory", MISSING)
    metadata = {"_names": names, **kwargs}
    return field(default=default, default_factory=default_factory, metadata=metadata)


def arg(**kwargs):
    default = kwargs.pop("default", MISSING)
    if default == argparse.SUPPRESS:
        raise UnsupportedException("SUPPRESS is unsupported in dataclass_opt")
    default_factory = kwargs.pop("default_factory", MISSING)
    return field(default=default, default_factory=default_factory, metadata=kwargs)


_parsing_args = False


class DataClassParser(ArgumentParser):
    def __init__(self, *args, **kwargs):
        self.subparsers = None
        init_dataclass = None
        commands = {}
        version = None

        if args and is_dataclass(args[0]):
            init_dataclass = args[0]
            args = args[1:]
        if "args" in kwargs.keys():
            init_dataclass = kwargs.pop("args")
        if "command" in kwargs.keys():
            command = kwargs.pop("command")
            commands.update(_to_name_command_dict(command))
        if "commands" in kwargs.keys():
            cmds = kwargs.pop("commands")
            commands.update(_to_name_command_dict(cmds))
        if "version" in kwargs.keys():
            version = kwargs.pop("version")

        super().__init__(*args, **kwargs)

        if init_dataclass:
            self.add_arguments(init_dataclass)
            self.set_defaults(cls=init_dataclass)

        if version is not None:
            self.add_argument("--version", action="version", version=version)

        self.have_commands = False
        if commands:
            for name, command in commands.items():
                self.add_command(name, command)
            self.have_commands = True

    def add_command(self, name: str, cls, *, help: str = None, func=None):
        if not is_dataclass(cls):
            raise MustBeADataclass("{} must be a dataclass")

        if self.subparsers is None:
            self.subparsers = self.add_subparsers()

        if func:
            class_name = cls.__name__ + "_"
            cls = make_dataclass(
                class_name, fields=[("func", typing.Callable, field(default=func))], bases=(cls,)
            )

        cmd_parser = self.subparsers.add_parser(name, help=help)
        self._add_arguments(cls, parser=cmd_parser)
        cmd_parser.set_defaults(cmd_cls=cls)
        if func:
            cmd_parser.set_defaults(func=func)

        self.have_commands = True

        return cmd_parser

    def add_arguments(self, cls):
        if not is_dataclass(cls):
            raise MustBeADataclass("{} must be a dataclass")

        return self._add_arguments(cls, parser=self)

    def parse_known_args(self, args=None, namespace=None):
        global _parsing_args

        if _parsing_args:
            return super().parse_known_args(args=args, namespace=namespace)

        _parsing_args = True
        try:
            args, argv = super().parse_known_args(args=args, namespace=namespace)
        finally:
            _parsing_args = False

        cls_is_dataclass = "cls" in args and is_dataclass(args.cls)
        cmd_is_dataclass = "cmd_cls" in args and is_dataclass(args.cmd_cls)

        if not cls_is_dataclass and not cmd_is_dataclass:
            if self.have_commands:
                return (args, None), argv
            return args, argv

        data = {k: v for k, v in vars(args).items()}

        def get_dataclass_obj(cls, data):
            cls_fields = [f.name for f in fields(cls)]
            cls_data = {key: value for key, value in data.items() if key in cls_fields}
            return cls(**cls_data), cls_fields

        if cls_is_dataclass and cmd_is_dataclass:
            cls = data.pop("cls")
            cmd_cls = data.pop("cmd_cls")

            cls_obj, _ = get_dataclass_obj(cls, data)
            cmd_obj, _ = get_dataclass_obj(cmd_cls, data)

            return (cls_obj, cmd_obj), argv

        if cls_is_dataclass:  # and not cmd_is_dataclass
            cls = data.pop("cls")
            cls_obj, cls_fields = get_dataclass_obj(cls, data)
            other_data = {key: value for key, value in data.items() if key not in cls_fields}

            return (cls_obj, Namespace(**other_data)), argv

        # cmd_is_dataclass
        cmd_cls = data.pop("cmd_cls")
        cmd_obj, cmd_cls_fields = get_dataclass_obj(cmd_cls, data)
        other_data = {key: value for key, value in data.items() if key not in cmd_cls_fields}

        return (Namespace(**other_data), cmd_obj), argv

    def _add_arguments(self, cls, parser=None):
        """Create an argument parser from a dataclass."""
        if parser is None:
            parser = DataClassParser()

        for dc_field in fields(cls):
            metadata = dc_field.metadata
            if metadata.get("suppress"):
                continue

            names = list(_get_names(dc_field))
            is_arg = _is_arg(dc_field)

            # type
            default_arg_type, is_optional, is_list = _get_type(dc_field.type)
            arg_type = metadata.get("type", default_arg_type)

            # action
            default_action = _get_action(is_arg, arg_type)
            action = metadata.get("action", default_action)

            if action == "append_const":
                raise UnsupportedException("append_const is not yet supported")

            # const
            const = metadata.get("const")

            # default value
            if dc_field.default == MISSING and dc_field.default_factory == MISSING:
                default = None
            elif dc_field.default != MISSING:
                default = dc_field.default
            else:
                default = dc_field.default_factory()

            use_default = arg_type != bool and action not in [
                "store_true",
                "store_false",
            ]
            pass_null_default = is_optional

            # nargs
            if is_list and action is None:
                # Assume at least one argument; user can override with
                # arg(..., nargs=...) or opt(..., nargs=...)
                default_nargs = "+"
            elif is_arg and default:
                # argument with a default value
                default_nargs = "?"
            elif is_arg and default is None and is_optional:
                # explicitly marked as optional (default value will be None)
                default_nargs = "?"
            else:
                default_nargs = None

            nargs = metadata.get("nargs", default_nargs)

            # choices
            choices = metadata.get("choices")
            metavar = metadata.get("metavar")
            version = metadata.get("version")
            help = metadata.get("help")

            # required
            required = (
                dc_field.default == MISSING
                and dc_field.default_factory == MISSING
                and not is_optional
                and default_arg_type != bool
            )

            # all arguments
            kwargs = {}

            if action is not None:
                kwargs["action"] = action

            if nargs is not None:
                kwargs["nargs"] = nargs

            if const is not None:
                kwargs["const"] = const

            if (default is not None and use_default) or (default is None and pass_null_default):
                kwargs["default"] = default

            if arg_type is not None and action not in [
                "store_const",
                "append_const",
                "store_true",
                "store_false",
                "count",
            ]:
                kwargs["type"] = arg_type

            if choices is not None:
                kwargs["choices"] = choices

            if metavar is not None:
                kwargs["metavar"] = metavar

            if version is not None:
                kwargs["version"] = version

            if help is not None:
                kwargs["help"] = help

            if not is_arg and required is not None:
                kwargs["required"] = required

            if not is_arg:
                kwargs["dest"] = dc_field.name

            parser.add_argument(*names, **kwargs)

        return parser
