# Clang warning flags collection and parser

This project includes tools and lists to figure out all warning flags
that [clang compiler](http://clang.llvm.org/) has:

* [clang 3.2 warnings](warnings-clang-3.2.txt)
* [clang 3.3 warnings](warnings-clang-3.3.txt)
* [clang 3.4 warnings](warnings-clang-3.4.txt)
* [clang 3.5 warnings](warnings-clang-3.5.txt)
* [clang 3.6 warnings](warnings-clang-3.6.txt)
* [clang 3.7 warnings](warnings-clang-3.7.txt)

# Requirements

This uses [ANTLR](http://www.antlr.org/) as a parser generator to
parse clang's diagnostic groups definitions.

* [make](http://www.gnu.org/software/make/)
* [ANTLR4](http://www.antlr.org/)
* [Python 2.7](https://www.python.org/)
* [antlr4-python2-runtime](https://pypi.python.org/pypi/antlr4-python2-runtime/)

# Usage

After you have installed all the requirements and are able to run
ANTLR with `antlr4` command, just use following commands:

    make
    ./parse-clang-diagnostic-groups.py <path-to-clang-source>/include/clang/Basic/DiagnosticGroups.td
    ./parse-gcc-warning-options.py <path-to-gcc-source>/gcc/gcc/c-family/c.opt

And you'll get the list of all individual warning flags and their
dependencies that are in the requested compiler version.

