#!/usr/bin/env python2

from antlr4 import *
import sys
import TableGenLexer
import TableGenListener
import TableGenParser

show_class_name = False
top_nodes_only = False

for arg in sys.argv:
    if arg == "--show-class":
        show_class_name = True
    elif arg == "--top-nodes-only":
        top_nodes_only = True
    else:
        filename = arg

string_input = FileStream(filename)
lexer = TableGenLexer.TableGenLexer(string_input)
stream = CommonTokenStream(lexer)
parser = TableGenParser.TableGenParser(stream)
tree = parser.expression()


class ClangDiagnosticGroupsListener(TableGenListener.TableGenListener):
    def __init__(self):
        self.currentDefinitionName = None
        self.currentSwitchName = None
        self.currentClassDefinitionName = None
        self.currentReferences = None
        self.switchClassesReferences = {}
        self.switchNames = {}
        self.switchClasses = {}

    def enterEmptySwitchName(self, ctx):
        if self.currentClassDefinitionName == "DiagGroup":
            self.currentSwitchName = ""

    def enterSwitchText(self, ctx):
        if self.currentClassDefinitionName == "DiagGroup":
            self.currentSwitchName = ctx.getText()

    def enterDefinitionName(self, ctx):
        self.currentDefinitionName = ctx.getText()

    def exitSwitchDefinition(self, ctx):
        self.currentDefinitionName = None

    def exitClassDefinition(self, ctx):
        if self.currentClassDefinitionName == "DiagGroup":
            if self.currentSwitchName is not None:
                self.switchNames[self.currentSwitchName] = self.currentDefinitionName
                self.switchClassesReferences[self.currentSwitchName] = self.currentReferences
            if self.currentDefinitionName:
                self.switchClasses[self.currentDefinitionName] = self.currentSwitchName
        self.currentSwitchName = None
        self.currentClassDefinitionName = None
        self.currentReferences = None

    def enterClassDefinitionName(self, ctx):
        self.currentClassDefinitionName = ctx.getText()
        if self.currentClassDefinitionName == "DiagGroup":
            self.currentReferences = []

    def enterIdentifierReference(self, ctx):
        self.currentReferences.append(ctx.getText())


diagnostics = ClangDiagnosticGroupsListener()
walker = ParseTreeWalker()
walker.walk(diagnostics, tree)


def class_name_string(class_name):
    string = ""
    if show_class_name:
        string = class_name or " <<<NONE>>>"
    return string

def print_references(diagnostics, switch_name, level):
    references = diagnostics.switchClassesReferences.get(switch_name, [])
    reference_switches = []
    for reference_class_name in references:
        reference_switch_name = diagnostics.switchClasses[reference_class_name]
        reference_switches.append(reference_switch_name)
    for reference_switch_name in sorted(reference_switches):
        class_name = \
            class_name_string(diagnostics.switchNames[reference_switch_name])
        switch_string = "%s-W%s" % ("  " * level, reference_switch_name)
        print "# {0:50} {1}".format(switch_string, class_name)
        print_references(diagnostics, reference_switch_name, level + 1)

def is_root_node(diagnostics, switch_name):
    for this_name in sorted(diagnostics.switchNames.keys()):
        references = diagnostics.switchClassesReferences.get(this_name, [])
        for reference_class_name in references:
            reference_switch_name = \
                diagnostics.switchClasses[reference_class_name]
            if switch_name == reference_switch_name:
                return False
    return True

for name in sorted(diagnostics.switchNames.keys()):
    if not top_nodes_only or is_root_node(diagnostics, name):
        class_name = class_name_string(diagnostics.switchNames[name])
        print "-W{0:50} {1}".format (name, class_name)
        print_references(diagnostics, name, 1)

