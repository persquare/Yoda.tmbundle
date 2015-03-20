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

def signature():
    script = get_script()
    completions = script.call_signatures()
    if not completions:
        return

    signatures = []
    for c in completions:
        names = [p.name for p in c.params]
        display = ', '.join(names)
        signatures.append(display)
    if not signatures:
        return
    if len(signatures) == 1:
        sys.stdout.write(signatures[0])
        return
    # Prepare data for popup
    suggestions = [{'display':s} for s in signatures]
    return present_popup(suggestions)
