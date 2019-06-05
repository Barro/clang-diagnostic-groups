#!/usr/bin/env python3

import argparse
import antlr4
import common
import sys

import GccOptionsLexer
import GccOptionsListener
import GccOptionsParser

STATE_COMMENT = 1
STATE_OPTION_NAME = 2
STATE_OPTION_ATTRIBUTES = 3
STATE_OPTION_DESCRIPTION = 4
STATE_NEWLINE = 5

BORING_OPTIONS = set(["Variable", "Enum", "EnumValue"])

NON_WARNING_WS = set([
    "Werror",
    "Werror=",
    "Wfatal-errors",
])

WARNINGS_NON_W = set([
    "pedantic",
])

# Many of these go into common.opt in GCC 4.6 but before that they are aliases:
HIDDEN_WARNINGS = [
    # Pedantic is always in but in the options file it is only in 4.8 and later
    # GCC versions.
    ("pedantic", []),
    ("-all-warnings", ["Wall"]),
    ("-extra-warnings", ["Wextra"]),
    ("-pedantic", ["pedantic"]),
    ("W", ["Wextra"]),
]


def parse_warning_blocks(fp):
    blocks = []
    state = STATE_COMMENT
    for line in fp:
        line = line.rstrip("\n")
        if state == STATE_OPTION_DESCRIPTION and line != "":
            continue

        if state == STATE_OPTION_DESCRIPTION and line == "":
            state = STATE_NEWLINE
            continue

        if state == STATE_NEWLINE:
            if line.startswith(";"):
                state == STATE_COMMENT
                continue
            if line == "":
                continue
            option_name = line
            state = STATE_OPTION_NAME
            continue

        if state == STATE_COMMENT:
            if line.startswith(";"):
                continue
            if line == "":
                state = STATE_NEWLINE
                continue

        if state == STATE_OPTION_NAME:
            state = STATE_OPTION_DESCRIPTION
            if option_name in BORING_OPTIONS:
                continue
            # if not option_name.startswith("W"):
            #     continue
            option_attributes = line
            blocks.append((option_name, option_attributes))
            continue
    return blocks


def apply_listener(string_value, listener):
    string_input = antlr4.InputStream(string_value)
    lexer = GccOptionsLexer.GccOptionsLexer(string_input)
    stream = antlr4.CommonTokenStream(lexer)
    parser = GccOptionsParser.GccOptionsParser(stream)
    tree = parser.optionAttributes()
    walker = antlr4.ParseTreeWalker()
    walker.walk(listener, tree)


class VariableAssignmentListener(GccOptionsListener.GccOptionsListener):
    """
    >>> listener = VariableAssignmentListener()
    >>> apply_listener("Var(varname)", listener)
    >>> listener.variable_name
    'varname'
    """

    def __init__(self):
        self.variable_name = None
        self._last_name = None

    def enterVariableName(self, ctx):
        self._last_name = ctx.getText()

    def enterAtom(self, ctx):
        if self._last_name == "Var":
            self.variable_name = ctx.getText()

    def exitTrailer(self, ctx):
        self._last_name = None


class AliasAssignmentListener(GccOptionsListener.GccOptionsListener):
    """
    >>> listener = AliasAssignmentListener()
    >>> apply_listener("Alias(Wall)", listener)
    >>> listener.alias_name
    'Wall'
    >>> listener = AliasAssignmentListener()
    >>> apply_listener("Alias(Wformat=,1,0)", listener)
    >>> listener.alias_name
    'Wformat=1'
    """

    def __init__(self):
        self.alias_name = None
        self._last_name = None
        self._argument_id = 0

    def enterVariableName(self, ctx):
        self._last_name = ctx.getText()
        self._argument_id = 0

    def enterArgument(self, ctx):
        self._argument_id += 1

    def enterAtom(self, ctx):
        if self._last_name == "Alias" and self._argument_id == 1:
            self.alias_name = ctx.getText()
        if self._last_name == "Alias" and self._argument_id == 2:
            self.alias_name += ctx.getText()

    def exitTrailer(self, ctx):
        self._last_name = None


class LanguagesEnabledListener(GccOptionsListener.GccOptionsListener):
    """
    Listens to LangEnabledBy(languagelist,warningflags) function calls

    "warningflags" are the most interesting ones, as it means that this warning
    is enabled by another flag.

    >>> listener = LanguagesEnabledListener()
    >>> apply_listener("LangEnabledBy(C C++,Wall,0,1)", listener)
    >>> listener.flags
    ['Wall']

    >>> listener = LanguagesEnabledListener()
    >>> apply_listener("LangEnabledBy(C C++,Wall99,0,1)", listener)
    >>> listener.flags
    ['Wall99']

    >>> listener = LanguagesEnabledListener()
    >>> apply_listener("LangEnabledBy(C C++,Wall || Wc++-compat)", listener)
    >>> listener.flags
    ['Wall', 'Wc++-compat']
    """

    def __init__(self):
        self._last_name = None
        self._argument_id = 0
        self.flags = []

    def enterVariableName(self, ctx):
        if ctx.getText() == "LangEnabledBy":
            self._last_name = "LangEnabledBy"
            self._argument_id = 0

    def enterArgument(self, ctx):
        self._argument_id += 1

    def enterAtom(self, ctx):
        if self._last_name == "LangEnabledBy" and self._argument_id == 2:
            flag_name = ctx.getText()
            self.flags.append(flag_name)

    def exitTrailer(self, ctx):
        self._last_name = None


class EnabledByListener(GccOptionsListener.GccOptionsListener):
    """
    Listens to EnabledBy(warningflag) function calls

    >>> listener = EnabledByListener()
    >>> apply_listener("EnabledBy(Wextra)", listener)
    >>> listener.enabled_by
    'Wextra'
    """

    def __init__(self):
        self._last_name = None
        self.enabled_by = None

    def enterVariableName(self, ctx):
        if ctx.getText() == "EnabledBy":
            self._last_name = "EnabledBy"

    def enterAtom(self, ctx):
        if self._last_name == "EnabledBy":
            self.enabled_by = ctx.getText()

    def exitTrailer(self, ctx):
        self._last_name = None


class DefaultsListener(GccOptionsListener.GccOptionsListener):
    """
    Listens to attributes to infer 'enabled by default' status

    This attempts to infer whether an option is enabled by default by use of
    idioms. The implementation favors type II errors (missing an enabled-by-
    default case) over type I errors (marking a flag as enabled-by-default
    when it is not).

    - Presence of Enum, UInteger, or Joined indicates this is not an on-off
      switch
    - A value of '1' or '-1' typically means on by default
    - A value of '0' typically means off by default
    - Another numeric value typically signifies more complex logic is used,
      such as for trigraphs.
    - A non-numeric value is a configure symbol, so this script cannot be sure.

    >>> listener = DefaultsListener()
    >>> apply_listener("Init(1)", listener)
    >>> listener.isEnabledByDefault()
    True
    >>> listener = DefaultsListener()
    >>> apply_listener("Init(-1)", listener)
    >>> listener.isEnabledByDefault()
    True
    >>> listener = DefaultsListener()
    >>> apply_listener("Init(0)", listener)
    >>> listener.isEnabledByDefault()
    False
    >>> listener = DefaultsListener()
    >>> apply_listener("Init(2)", listener)
    >>> listener.isEnabledByDefault()
    False
    >>> listener = DefaultsListener()
    >>> apply_listener("Init(COND)", listener)
    >>> listener.isEnabledByDefault()
    False
    >>> listener = DefaultsListener()
    >>> apply_listener("UInteger Init(1)", listener)
    >>> listener.isEnabledByDefault()
    False
    >>> listener = DefaultsListener()
    >>> apply_listener("Init(1) Enum", listener)
    >>> listener.isEnabledByDefault()
    False
    >>> listener = DefaultsListener()
    >>> apply_listener("Init(-1) Joined", listener)
    >>> listener.isEnabledByDefault()
    False
    """

    def __init__(self):
        self._last_name = None
        self._init_value = None
        self._is_boolean = True

    def enterVariableName(self, ctx):
        if ctx.getText() == "Init":
            self._last_name = "Init"
        elif ctx.getText() in ("Enum", "Joined", "UInteger"):
            self._is_boolean = False

    def enterAtom(self, ctx):
        if self._last_name == "Init":
            self._init_value = ctx.getText()

    def exitTrailer(self, ctx):
        self._last_name = None

    def isEnabledByDefault(self):
       return self._is_boolean and self._init_value in ("1", "-1")


class WarningOptionListener(GccOptionsListener.GccOptionsListener):
    """
    Searches for Warning attributes.

    >>> listener = WarningOptionListener()
    >>> apply_listener("C C++ Warning", listener)
    >>> listener.is_warning
    True

    Search for warn_* variables:

    >>> listener = WarningOptionListener()
    >>> apply_listener("C C++ Var(warn_sign_conversion) Init(-1)", listener)
    >>> listener.is_warning
    True
    """

    def __init__(self):
        self._last_name = None
        self.is_warning = False

    def enterVariableName(self, ctx):
        if ctx.getText() == "Warning":
            self.is_warning = True
        elif ctx.getText() == "Var":
            self._last_name = "Var"

    def enterAtom(self, ctx):
        if self._last_name != "Var":
            return
        if ctx.getText().startswith("warn_"):
            self.is_warning = True

    def exitTrailer(self, ctx):
        self._last_name = None


class DummyWarningListener(GccOptionsListener.GccOptionsListener):
    """
    Checks if switch does nothing.

    >>> listener = DummyWarningListener()
    >>> apply_listener("C C++ Warning Ignore", listener)
    >>> listener.is_dummy
    True
    """

    def __init__(self):
        self.is_dummy = False

    def enterVariableName(self, ctx):
        if ctx.getText() == "Ignore":
            self.is_dummy = True


def print_child_option(option_name, level):
    print("# " + "  " * level, "-" + option_name)


def print_default_options(defaults, references):
    if len(defaults) == 0:
        return

    print("# enabled by default:")

    for option_name in sorted(defaults):
        print_child_option(option_name, 1)
        print_enabled_options(references, option_name, 2)


def print_enabled_options(references, option_name, level=1):
    for reference in sorted(
            references.get(option_name, []), key=lambda x: x.lower()):
        print_child_option(reference, level)
        if reference in references:
            print_enabled_options(references, reference, level + 1)


def could_be_warning(option_name, option_arguments):
    if "," in option_name:
        return False
    if option_name in NON_WARNING_WS:
        return False

    return option_name.startswith("W")


def parse_options_file(filename):
    blocks = parse_warning_blocks(open(filename))

    references = {}
    aliases = {}
    warnings = set()
    dummies = set()
    defaults = set()

    for option_name, option_arguments in blocks:
        warning_option = WarningOptionListener()
        apply_listener(option_arguments, warning_option)

        if warning_option.is_warning:
            warnings.add(option_name)
        elif could_be_warning(option_name, option_arguments):
            warnings.add(option_name)

        if option_name not in references:
            references[option_name] = []

        dummy_option = DummyWarningListener()
        apply_listener(option_arguments, dummy_option)
        if dummy_option.is_dummy:
            dummies.add(option_name)

        language_enablers = LanguagesEnabledListener()
        apply_listener(option_arguments, language_enablers)
        for flag in language_enablers.flags:
            if flag not in references:
                references[flag] = []
            references[flag].append(option_name)

        flag_enablers = EnabledByListener()
        apply_listener(option_arguments, flag_enablers)
        if flag_enablers.enabled_by:
            flag = flag_enablers.enabled_by
            if flag not in references:
                references[flag] = []
            references[flag].append(option_name)

        bydefault_option = DefaultsListener()
        apply_listener(option_arguments, bydefault_option)
        if bydefault_option.isEnabledByDefault():
            defaults.add(option_name)

        alias_enablers = AliasAssignmentListener()
        apply_listener(option_arguments, alias_enablers)
        if alias_enablers.alias_name is not None:
            aliases[option_name] = alias_enablers.alias_name

    return references, aliases, warnings, dummies, defaults


def create_dummy_text(dummies, switch_name):
    if switch_name in dummies:
        return " # DUMMY switch"
    return ""


def create_defaults_text(defaults, switch_name):
    if switch_name in defaults:
        return " # (enabled by default)"
    return ""


def print_warning_flags(args, references, parents, aliases, warnings, dummies, defaults):
    if args.top_level:
        # Print a group that has all enabled-by-default warnings together
        print_default_options(warnings.intersection(defaults), references)

    for option_name in sorted(references.keys(), key=lambda x: x.lower()):
        option_aliases = aliases.get(option_name, [])
        if option_name not in warnings:
            is_warning = False
            for alias in option_aliases:
                if alias in warnings:
                    is_warning = True
                    break
            if not is_warning:
                continue

        dummy_text = create_dummy_text(dummies, option_name)
        defaults_text = create_defaults_text(defaults, option_name)
        if args.unique:
            print("-%s%s%s" % (option_name, defaults_text, dummy_text))
            continue

        if args.top_level:
            if option_name in aliases:
                continue
            if option_name in defaults:
                continue
            if len(parents.get(option_name, set())) > 0:
                continue

        if option_name in aliases:
            sorted_aliases = sorted(
                aliases[option_name], key=lambda x: x.lower())
            print("-%s = -%s%s" % (
                option_name, ", -".join(sorted_aliases), dummy_text))
        else:
            print("-%s%s" % (option_name, dummy_text))
        print_enabled_options(references, option_name)


def main(argv):
    parser = argparse.ArgumentParser(description="""\
Parses GCC option files for warning options.""")
    common.add_common_parser_options(parser)
    parser.add_argument("option_file", metavar="option-file", nargs="+")
    args = parser.parse_args(argv[1:])

    all_references = {}
    all_aliases = {}
    all_warnings = set()
    all_dummies = set()
    all_defaults = set()

    for switch, aliases in HIDDEN_WARNINGS:
        all_references[switch] = set()
        all_warnings.add(switch)
        if len(aliases):
            all_aliases[switch] = set(aliases)

    for filename in args.option_file:
        (file_references,
         file_aliases,
         file_warnings,
         file_dummies,
         file_defaults) = parse_options_file(filename)
        for flag, reference in file_references.items():
            references = all_references.get(flag, set())
            all_references[flag] = references.union(reference)
        for flag, alias in file_aliases.items():
            aliases = all_aliases.get(flag, set())
            aliases.add(alias)
            all_aliases[flag] = aliases
        all_warnings = all_warnings.union(file_warnings)
        all_dummies = all_dummies.union(file_dummies)
        all_defaults = all_defaults.union(file_defaults)

    all_parents = {}
    for flag, references in all_references.items():
        for reference in references:
            parents = all_parents.get(reference, set())
            parents.add(flag)
            all_parents[reference] = parents

    print_warning_flags(
        args,
        all_references,
        all_parents,
        all_aliases,
        all_warnings,
        all_dummies,
        all_defaults
        )

if __name__ == "__main__":
    main(sys.argv)
