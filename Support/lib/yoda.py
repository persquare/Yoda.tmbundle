#!/usr/bin/env python3

# based on python-jedi.tmbundle/completions.py
# <https://github.com/lawrenceakka/python-jedi.tmbundle>
import os
import sys
import functools

import jedi


# Jedi API overview: https://jedi.readthedocs.io/en/latest/docs/api.html

# The following jedi functionality is used:
# -----------------------------------------
#   script.completions()
#   script.call_signatures()
#   script.usages()
#   script.goto_definitions()
#   script.goto_assignments()

# Consider using the following:
# -----------------------------
# Name.get_signatures() -> List[Signature]. Signatures are similar to CallSignature.
#   Name.params is therefore deprecated.
# Signature.to_string() to format signatures.
# Signature.params -> List[ParamName], ParamName has the following additional attributes infer_default(),
#   infer_annotation(), to_string(), and kind.
# Name.execute() -> List[Name], makes it possible to infer return values of functions.
# Script(...).completions(fuzzy=True)
# Added Project support. This allows a user to specify which folders Jedi should work with.
# Added support for Refactoring. The following refactorings have been implemented:
#   Script.rename, Script.inline, Script.extract_variable and Script.extract_function.
# Added Script.get_syntax_errors to display syntax errors in the current script.
# Added code search capabilities both for individual files and projects.
#   The new functions are Project.search, Project.complete_search, Script.search and Script.complete_search.
# Added Script.help to make it easier to display a help window to people.
#   Now returns pydoc information as well for Python keywords/operators.

# Notes
# -----
# Big Script API Changes:
#   The line and column parameters of jedi.Script are now deprecated
#   completions deprecated, use complete instead
#   goto_assignments deprecated, use goto instead
#   goto_definitions deprecated, use infer instead
#   call_signatures deprecated, use get_signatures instead
#   usages deprecated, use get_references instead
#   jedi.names deprecated, use jedi.Script(...).get_names()


try:
    envvars = ['TM_PYTHON_HELPERS_BUNDLE_SUPPORT', 'TM_BUNDLE_SUPPORT']
    sys.path[:0] = [os.path.join(os.environ[v], 'lib') for v in envvars]
except:
    errmsg = """
    The PythonHelpers bundle required, see<br/>
    <a href=https://github.com/persquare/PythonHelpers.tmbundle>
    github.com/persquare/PythonHelpers.tmbundle
    </a>
    """
    sys.stderr.write(errmsg)
    sys.exit(205)

# import TextMate as tm
from TextMate import dialog

env = os.environ


def open_in_editor(path, line=1, column=0):
    # os.system("open txmt://open/?url=file:///%s&line=%d&column=%d" % (path, int(line), int(column)))
    os.system("mate -l%d:%d %s" % (int(line), int(column), path))

def _active_selection():
    return 'TM_SELECTED_TEXT' in env


def _get_line_column():
    if _active_selection():
        lc, _ = env['TM_SELECTION'].split('-', 1)
        line, col = lc.split(':')
    else:
        line = env['TM_LINE_NUMBER']
        col = env['TM_COLUMN_NUMBER']
    return (int(line), int(col)-1)


def get_script(debug=None):
    """ Get the Jedi script object from the source passed on stdin, or none"""
    source = ''.join(sys.stdin.readlines()) or debug
    script = None
    try:
        line, col = _get_line_column() if not debug else (1, len(debug))
        # encoding = tm_query.query('encoding')
        path = env['TM_FILE_PATH'] if not source else None
        script = jedi.Script(source, line, col, path)
    except Exception as e: # AttributeError, KeyError:
        dialog.present_tooltip("{}".format(e))
        pass
    return script

def completion():
    script = get_script()
    completions = script.completions()
    if not completions:
        return
    if len(completions) == 1:
        sys.stdout.write(completions[0].complete)
        return
    # Prepare data for popup
    icons = dialog.register_images(env['TM_BUNDLE_SUPPORT'] + '/icons')
    typed = env.get('TM_CURRENT_WORD', '').lstrip('.')
    suggestions = [{'display':c.name, 'image':c.type if c.type in icons else 'none'} for c in completions]
    dialog.present_popup(suggestions, typed)


def _prep_arg(arg, i):
    return '${%d:%s}' % (i, arg.strip())

def _prep_karg(karg, i):
    param, default = karg.strip().split('=')
    return '%s=${%d:%s}' % (param, i, default)


def _prepare_arg_snippets(descriptions):
    args = []
    kargs = []
    vargs = []
    i = 0
    for d in descriptions:
        i = i + 1
        if '*' in d:
            vargs.append(_prep_arg(d, i))
        elif '=' in d:
            kargs.append(_prep_karg(d, i))
        else:
            args.append(_prep_arg(d, i))
    return (args, kargs, vargs)


def signature():
    script = get_script()
    completions = script.call_signatures()
    if not completions:
        return

    signatures = []
    # Really don't know when we could get > 1 result here...
    # Discard for now, and use headings for grouping if I find out it happens
    if len(completions)>1:
        dialog.present_tooltip("Mutiple options\n"+str(completions))

    c = completions[0]
    descriptions = [p.description.rstrip(', ') for p in c.params]

    # Truncate descriptions if we've already filled in some params
    # FIXME: Only works properly for positional parameters
    descriptions = descriptions[c.index:]

    args, kargs, vargs = _prepare_arg_snippets(descriptions)

    # Present (up to) three options:
    # 1) only positional arguments
    # 2) positional and named arguments
    # 3) all arguments
    minimal = args
    sensible = args + kargs
    maximal = args + kargs + vargs

    minimal_key = ', '.join(descriptions[:len(minimal)])
    sensible_key = ', '.join(descriptions[:len(sensible)])
    maximal_key = ', '.join(descriptions[:len(maximal)])

    options = {}
    if minimal_key: options[minimal_key] = ', '.join(minimal)
    if sensible_key: options[sensible_key] = ', '.join(sensible)
    if maximal_key: options[maximal_key] = ', '.join(maximal)

    if not options:
        return

    if len(options) == 1:
        sys.stdout.write(options.values()[0])
        sys.exit(204)

    selection = tuple(options.keys())
    choice = dialog.present_menu(selection)
    if choice is not None:
        key = selection[choice]
        sys.stdout.write(options[key])
        sys.exit(204)


def _goto_description(description):
    # description is instance of Definition()
    if description.in_builtin_module():
        dialog.present_tooltip("builtin: %s" % description.description)
        return
    file = description.module_path or env['TM_FILEPATH'] if 'TM_FILEPATH' in env else None
    if not file:
        dialog.present_tooltip("Unknown location")
        return
    # Actually goto selected location here...
    # present_tooltip("Jumping to %s:%s" % (file, description.line))
    open_in_editor(file, description.line, description.column)

def _cmp(a, b):
    return (a > b) - (a < b)

def _usage_cmp(a, b):
    order = _cmp(a.module_name, b.module_name)
    if order == 0:
        order = _cmp(a.line, b.line)
    return order

def _process_usages(us):
    # Sort per file:line
    us.sort(key=functools.cmp_to_key(_usage_cmp))
    # FIXME: Move definition to top? (OTOH that is handled by goto definition)
    options = {}
    menu_items = []
    for u in us:
        file = env['TM_FILENAME'] if 'TM_FILENAME' in env else '---'
        key = "[%s:%s] %s" % (u.module_name or file, u.line, u.description)
        options[key] = u
        menu_items.append(key)
    # Return menu_items to preserve ordering
    return (menu_items, options)


def usage():
    script = get_script()
    usages = script.usages()
    if not usages:
        return

    menu_items, options = _process_usages(usages)
    choice = dialog.present_menu(menu_items)
    if choice is not None:
        key = menu_items[choice]
        _goto_description(options[key])

def definitions():
    script = get_script()
    definitions = script.goto_definitions()
    if not definitions:
        return
    if len(definitions) == 1:
        _goto_description(definitions[0])
        return
    menu_items, options = _process_usages(definitions)
    choice = dialog.present_menu(menu_items)
    if choice is not None:
        key = menu_items[choice]
        _goto_description(options[key])

def assignments():
    script = get_script()
    assignments = script.goto_assignments()
    if not assignments:
        return
    if len(assignments) == 1:
        _goto_description(assignments[0])
        return
    menu_items, options = _process_usages(assignments)
    choice = dialog.present_menu(menu_items)
    if choice is not None:
        key = menu_items[choice]
        _goto_description(options[key])

def quickdoc():
    """Present tooltip with short docs"""
    script = get_script()
    if script is None:
        return
    try:
        definitions = script.goto_definitions()
    except jedi.NotFoundError:
        dialog.present_tooltip('No definition found')
        return

    if definitions:
        definition = definitions[0]
        dialog.present_tooltip(definition.docstring())
