import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, TextIO

from pytest import raises

from dataclass_opt import (
    SUPPRESS,
    DataClassParser,
    FileType,
    Namespace,
    UnsupportedException,
    arg,
    opt,
)

# from dataclass_opt import BooleanOptionalAction


def test_no_fields():
    @dataclass
    class Test:
        pass

    parser = DataClassParser(Test)
    args = parser.parse_args([])
    assert args == Test()

    with raises(SystemExit):
        parser.parse_args(["--name", "Jim"])


def test_required_args():
    @dataclass
    class Test:
        string: str
        integer: int

    parser = DataClassParser(Test)
    args = parser.parse_args(["abc", "10"])
    assert args == Test("abc", 10)

    with raises(SystemExit):
        parser.parse_args(["abc"])


def test_optional_args():
    @dataclass
    class Test:
        string: str = "abc"
        integer: int = 10

    parser = DataClassParser(Test)
    args = parser.parse_args([])
    assert args == Test("abc", 10)

    args = parser.parse_args(["foo"])
    assert args == Test("foo", 10)


def test_required_and_optional():
    @dataclass
    class Test:
        bar: str
        foo: str = opt()

    parser = DataClassParser(Test)
    args = parser.parse_args("BAR --foo FOO".split())
    assert args == Test("BAR", "FOO")

    args = parser.parse_args("BAR -f FOO".split())
    assert args == Test("BAR", "FOO")


def test_optional_no_short():
    @dataclass
    class Test:
        foo: str = opt(short=None)

    parser = DataClassParser(Test)
    args = parser.parse_args("--foo FOO".split())
    assert args == Test("FOO")

    with raises(SystemExit):
        parser.parse_args("-f FOO".split())


def test_optional_no_long():
    @dataclass
    class Test:
        foo: str = opt(long=None)

    parser = DataClassParser(Test)
    args = parser.parse_args("-f FOO".split())
    assert args == Test("FOO")

    with raises(SystemExit):
        parser.parse_args("--foo FOO".split())


def test_store_const_optional():
    @dataclass
    class Test:
        foo: Optional[int] = opt(action="store_const", const=42)

    parser = DataClassParser(Test)
    args = parser.parse_args(["--foo"])
    assert args == Test(42)

    args = parser.parse_args(["-f"])
    assert args == Test(42)

    args = parser.parse_args([])
    assert args == Test(None)


def test_store_const_with_default():
    @dataclass
    class Test:
        foo: int = opt(action="store_const", const=42, default=41)

    parser = DataClassParser(Test)
    args = parser.parse_args(["--foo"])
    assert args == Test(42)

    args = parser.parse_args(["-f"])
    assert args == Test(42)

    args = parser.parse_args([])
    assert args == Test(41)


def test_store_true_false():
    @dataclass
    class Test:
        foo: bool = opt(short=None)
        bar: bool = opt(short=None, action="store_false")
        baz: bool = opt(short=None, action="store_false")

    parser = DataClassParser(Test)
    args = parser.parse_args("--foo --bar".split())
    assert args == Test(True, False, True)


def test_append_str():
    @dataclass
    class Test:
        foo: List[str] = opt(action="append")

    parser = DataClassParser(Test)
    args = parser.parse_args("--foo 1 --foo 2".split())
    assert args == Test(["1", "2"])


def test_append_int():
    @dataclass
    class Test:
        foo: List[int] = opt(action="append")

    parser = DataClassParser(Test)
    args = parser.parse_args("--foo 1 --foo 2".split())
    assert args == Test([1, 2])


def test_append_const():
    # TODO: we should be able to support "append_const",
    # but it's a little awkward, and would require some refactoring.

    @dataclass
    class Test:
        foo: List[int] = opt(action="append_const")

    with raises(UnsupportedException):
        DataClassParser(Test)


def test_count():
    @dataclass
    class Test:
        verbose: int = opt(action="count", default=0)

    parser = DataClassParser(Test)
    args = parser.parse_args(["-vvv"])
    assert args == Test(3)

    args = parser.parse_args([])
    assert args == Test(0)


def test_version():
    @dataclass
    class Test:
        pass

    parser = DataClassParser(Test, version="1.0")
    with raises(SystemExit):
        parser.parse_args(["--version"])


# Maybe Python 3.9 only?

# def test_boolean_optional():
#     @dataclass
#     class Test:
#         foo: Optional[bool] = opt(action=BooleanOptionalAction)

#     parser = DataClassParser(Test)
#     args = parser.parse_args(["--foo"])
#     assert args == Test(True)

#     args = parser.parse_args(["--no-foo"])
#     assert args == Test(True)

#     args = parser.parse_args([])
#     assert args == Test(None)


def test_nargs():
    @dataclass
    class Test:
        foo: List[str] = opt(nargs=2)
        bar: List[str] = arg(nargs=1)

    parser = DataClassParser(Test)
    args = parser.parse_args("c --foo a b".split())
    assert args == Test(["a", "b"], ["c"])


def test_nargs_optional():
    @dataclass
    class Test:
        foo: str = opt(nargs="?", const="c", default="d")
        bar: str = arg(nargs="?", default="d")

    parser = DataClassParser(Test)
    args = parser.parse_args("XX --foo YY".split())
    assert args == Test("YY", "XX")

    args = parser.parse_args("XX --foo".split())
    assert args == Test("c", "XX")

    args = parser.parse_args([])
    assert args == Test("d", "d")


def test_nargs_stdin_stdout():
    @dataclass
    class Test:
        infile: TextIO = arg(nargs="?", type=FileType("r"), default=sys.stdin)
        outfile: TextIO = arg(nargs="?", type=FileType("w"), default=sys.stdout)

    with tempfile.TemporaryDirectory() as tmpdirname:
        infile = str(Path(tmpdirname) / "input.txt")
        outfile = str(Path(tmpdirname) / "output.txt")
        with open(infile, "w") as f:
            print("hello world", file=f)

        parser = DataClassParser(Test)
        args = parser.parse_args([infile, outfile])
        assert isinstance(args, Test)
        assert args.infile.name == infile
        assert args.outfile.name == outfile

        args.infile.close()
        args.outfile.close()


def test_nargs_star():
    @dataclass
    class Test:
        foo: List[str] = opt(nargs="*")
        bar: List[str] = opt(nargs="*")
        baz: List[str] = arg(nargs="*")

    parser = DataClassParser(Test)
    args = parser.parse_args("a b --foo x y --bar 1 2".split())
    assert args == Test(["x", "y"], ["1", "2"], ["a", "b"])


def test_nargs_plus():
    @dataclass
    class Test:
        foo: List[str] = arg(nargs="+")

    parser = DataClassParser(Test)
    args = parser.parse_args("a b c".split())
    assert args == Test(["a", "b", "c"])

    with raises(SystemExit):
        parser.parse_args([])


def test_default():
    @dataclass
    class Test:
        foo: int = opt(default=42)

    parser = DataClassParser(Test)
    args = parser.parse_args("--foo 2".split())
    assert args == Test(2)

    args = parser.parse_args([])
    assert args == Test(42)


def test_default_conversions():
    @dataclass
    class Test:
        length: int = opt(default="10")
        width: int = opt(default=10.5)

    parser = DataClassParser(Test)
    args = parser.parse_args([])
    # Note: this is expected (if undesirable) behavior.
    # See https://docs.python.org/3/library/argparse.html#default
    assert args == Test(10, 10.5)


def test_default_suppress():
    with raises(UnsupportedException):

        @dataclass
        class Test:
            foo: int = opt(default=SUPPRESS)


def test_types():
    @dataclass
    class Test:
        count: int
        distance: float
        street: str = arg(type=ascii)
        code_point: int = arg(type=ord)
        source_file: TextIO = arg(type=open)
        dest_file: TextIO = arg(type=FileType("w"))
        datapath: Path

    parser = DataClassParser(Test)
    with tempfile.TemporaryDirectory() as tmpdirname:
        infile = str(Path(tmpdirname) / "input.txt")
        outfile = str(Path(tmpdirname) / "output.txt")
        with open(infile, "w") as f:
            print("hello world", file=f)

        args = parser.parse_args(["42", "6.28", "Main St.", "å", infile, outfile, tmpdirname])
        assert isinstance(args, Test)
        assert args.count == 42
        assert args.distance == 6.28
        assert args.street == ascii("Main St.")
        assert args.code_point == ord("å")
        assert args.source_file.name == infile
        assert args.dest_file.name == outfile
        assert args.datapath == Path(tmpdirname)

        args.source_file.close()
        args.dest_file.close()


def test_choices():
    @dataclass
    class Test:
        move: str = arg(choices=["rock", "paper", "scissors"])

    parser = DataClassParser(Test)
    args = parser.parse_args(["rock"])
    assert args == Test("rock")

    with raises(SystemExit):
        parser.parse_args(["fire"])


def test_choices_int():
    @dataclass
    class Test:
        door: int = arg(choices=range(1, 4))

    parser = DataClassParser(Test)
    args = parser.parse_args(["3"])
    assert args == Test(3)

    with raises(SystemExit):
        parser.parse_args(["4"])


def test_required():
    @dataclass
    class Test:
        foo: str = opt()

    parser = DataClassParser(Test)
    args = parser.parse_args("--foo BAR".split())
    assert args == Test("BAR")

    with raises(SystemExit):
        parser.parse_args([])


def test_dest():
    sum_opt = opt(
        "--sum",
        action="store_const",
        const=sum,
        default=max,
        help="sum the integers (default: find the max)",
    )

    @dataclass
    class Test:
        integers: List[int] = arg(metavar="int", nargs="+", help="Any integer")
        accumulate: Callable = sum_opt

    parser = DataClassParser(Test)
    args = parser.parse_args(["2", "3", "4"])
    assert args == Test([2, 3, 4], accumulate=max)

    args = parser.parse_args(["--sum", "2", "3", "4"])
    assert args == Test([2, 3, 4], accumulate=sum)


def test_option_values():
    @dataclass
    class Test:
        x: bool = opt()
        y: bool = opt()
        z: str = opt()

    parser = DataClassParser(Test)
    args = parser.parse_args(["-xyzZ"])
    assert args == Test(True, True, "Z")


def test_invalid_args():
    @dataclass
    class Test:
        foo: int = opt()
        bar: Optional[str] = arg(nargs="?")

    parser = DataClassParser(Test)

    with raises(SystemExit):
        parser.parse_args(["--foo", "spam"])

    with raises(SystemExit):
        parser.parse_args(["--bar"])

    with raises(SystemExit):
        parser.parse_args(["spam", "badger"])


def test_subparsers():
    @dataclass
    class Test:
        foo: bool = opt()

    @dataclass
    class A:
        bar: int

    @dataclass
    class B:
        baz: Optional[str] = opt()

    parser = DataClassParser(Test, commands=[A, B])
    args, cmd_args = parser.parse_args("a 12".split())
    assert args == Test(False)
    assert cmd_args == A(12)

    args, cmd_args = parser.parse_args("--foo b --baz Z".split())
    assert args == Test(True)
    assert cmd_args == B("Z")

    args, cmd_args = parser.parse_args([])
    assert args == Test(False)
    assert cmd_args is None


def test_subparsers2():
    @dataclass
    class A:
        bar: int

    @dataclass
    class B:
        baz: Optional[str] = opt()

    parser = DataClassParser(commands=[A, B])
    parser.add_argument("--foo", action="store_true")

    args, cmd_args = parser.parse_args("a 12".split())
    assert args == Namespace(foo=False)
    assert cmd_args == A(12)

    args, cmd_args = parser.parse_args("--foo b --baz Z".split())
    assert args == Namespace(foo=True)
    assert cmd_args == B("Z")

    args, cmd_args = parser.parse_args([])
    assert args == Namespace(foo=False)
    assert cmd_args is None


def test_subparsers3():
    @dataclass
    class A:
        bar: int

    @dataclass
    class B:
        baz: Optional[str] = opt()

    parser = DataClassParser(commands=[A, B])

    args = parser.parse_args("a 12".split())
    assert args == A(12)

    args = parser.parse_args("b --baz Z".split())
    assert args == B("Z")

    args = parser.parse_args([])
    assert args is None
