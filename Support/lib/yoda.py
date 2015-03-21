# based on python-jedi.tmbundle/completions.py
# <https://github.com/lawrenceakka/python-jedi.tmbundle>
import os
import sys
import glob
import subprocess

env = os.environ
envvars = ['TM_BUNDLE_SUPPORT', 'TM_SUPPORT_PATH']
sys.path[:0] = [env[v]+b'/lib' for v in envvars if env[v] not in sys.path]

from plistlib import writePlistToString, readPlistFromString

# sys.path.insert(0, support_path + b'/jedi')
import jedi
jedi.settings.case_insensitive_completion = False
jedi.settings.add_bracket_after_function = True

dialog = env['DIALOG']

def _call_dialog(command, *args):
    """ Call the Textmate Dialog process

    command is the command to invoke.
    args are the strings to pass as arguments
    a dict representing the plist returned from DIALOG is returned

    """
    popen_args = [dialog, command]
    popen_args.extend(args)
    result = subprocess.check_output(popen_args)
    return result

def register_images(imgdir):
    imglist = glob.glob(imgdir+'/*.png')
    imgnames = [os.path.basename(img).rsplit('.', 1) for img in imglist]
    for (name, img) in zip(imgnames, imglist):
        _call_dialog('images', '--register', writePlistToString({name:img}))
    return imgnames

def present_popup(suggestions, typed='', extra_word_chars='_', return_choice=False):
    retval = _call_dialog('popup',
                          '--suggestions', writePlistToString(suggestions),
                          '--alreadyTyped', typed,
                          '--additionalWordCharacters', '_',
                          '--returnChoice' if return_choice else '')
    return readPlistFromString(retval) if retval else {}

def present_menu(menu_items):
    selections = [{'title':item} for item in menu_items]
    retval = _call_dialog('menu', '--items', writePlistToString(selections))
    return readPlistFromString(retval) if retval else {}

def present_tooltip(text, is_html=False):
    _call_dialog('tooltip', '--html' if is_html else '--text', text)


def get_script():
    """ Get the Jedi script object from the source passed on stdin, or none"""
    source = ''.join(sys.stdin.readlines()) or None
    script = None
    try:
        line = int(env['TM_LINE_NUMBER'])
        col = int(env['TM_COLUMN_NUMBER']) - 1
        # encoding = tm_query.query('encoding')
        path = env('TM_FILE_PATH') if not source else None
        script = jedi.Script(source, line, col, path)
    except (AttributeError, KeyError):
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
    icons = {}
    # register_images()
    typed = env.get('TM_CURRENT_WORD', '').lstrip('.')
    suggestions = [{'display':c.name, 'image':icons.get(c.name, 'green')} for c in completions]
    return present_popup(suggestions, typed)


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
    if len(completions)>1: present_tooltip("Mutiple options\n"+str(completions))
    
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
        sys.stdout.write(options.values[0])
        sys.exit(204)
    
    selection = present_menu(options.keys())
    if selection:
        key = selection['title']
        sys.stdout.write(options[key])
        sys.exit(204)

