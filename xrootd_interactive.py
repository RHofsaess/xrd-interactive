import argparse
import logging

import questionary

from xrootd_utils import _check_file_or_directory, _check_redirector, _sizeof_fmt
from xrootd_utils import (stat, stat_dir, ls, interactive_ls,
                          copy_file_to_remote, copy_file_from_remote, del_file, del_dir, mv, mkdir,
                          dir_size, create_file_list, get_file_size)

parser = argparse.ArgumentParser(
    description='xrootd python bindings for dummies')
parser.add_argument('-r', '--redirector', help='root://xrd-redirector:1094/')
parser.add_argument('-u', '--user', help='username', required=True)
parser.add_argument('-b', '--basepath', help='default: /store/user/', default='/store/user/')
parser.add_argument('-l', '--loglevel', help='python loglevel={"WARNING", "INFO", "DEBUG"}', default='INFO')
args = vars(parser.parse_args())

##################################################
basepath: str
redirector: str
redirector_type: str
user: str
##################################################

# set logging
FORMAT = '%(message)s'
logging.basicConfig(format=FORMAT)
log = logging.getLogger()

if args["loglevel"] is not None:
    log.setLevel(args["loglevel"])

# set user
user = args["user"]
###################################################

############################################
# first, select a redirector and base path #
############################################
if args["redirector"] is not None:
    # set and check redirector
    redirector = args["redirector"]
else:
    answers0 = questionary.form(
        _redirector=questionary.select('Please select a redirector:',
                                       choices=[
                                           'root://cmsxrootd-kit.gridka.de:1094/, (RW)',
                                           'root://cmsxrootd-redirectors.gridka.de:1094/, (RO)',
                                           'root://xrootd-cms.infn.it:1094/, EU redirector',
                                           'root://cmsxrootd.fnal.gov:1094/, US redirector',
                                           'root://cms-xrd-global.cern.ch:1094/, global redirector',
                                           'other'
                                       ])
    ).ask()
    if answers0["_redirector"] == 'other':
        redirector = str(input('Which redirector you want to use?'))
        if len(redirector) == 0:
            exit('No redirector specified! Please try again.')
    else:
        redirector = answers0["_redirector"].split(',')[0]  # take redirector from choices

log.info(f'Redirector selected: {redirector}')

# check type of the redirector: the behaviour of the bindings may differ!!
redirector_type = _check_redirector(redirector)  # not supported from dcache door
log.info(f'Redirector type: {redirector_type}')

# set and check base path
basepath = args["basepath"]
log.info(f'Selected base path: {basepath}')
if len(basepath) > 0 and (basepath[0] != '/' or basepath[-1] != '/'):
    exit('The base path has to begin and end with a "/"!')

log.debug(f'[DEBUG] All inputs: {user}, {basepath}, {redirector}, {args["loglevel"]}')
#####################
# Start questionary #
#####################
while True:
    answers = questionary.form(
        _function=questionary.select('What do you want to do?',
                                     choices=[
                                         'exit',
                                         'ls',
                                         'interactive ls',
                                         'stat',
                                         'stat directory',
                                         'dir size',
                                         'dir content',
                                         'rm file',
                                         'interactive file rm',
                                         'rm dir',
                                         'interactive dir rm',
                                         'mv',
                                         'mkdir',
                                         'copy file to',
                                         'copy file from',
                                         'create file list',
                                         'change base path',
                                         'change redirector',
                                         'help',
                                     ])
    ).ask()

    ########## exit ##########
    if answers["_function"] == 'exit':
        exit(0)

    ########## ls ##########
    if answers["_function"] == 'ls':
        answers1 = questionary.form(
            _directory=questionary.text(f'Which directory? \n>{basepath}')
        ).ask()
        ls(redirector, basepath + answers1["_directory"])

    ########## interactive ls ##########
    if answers["_function"] == 'interactive ls':
        answers1 = questionary.form(
            _directory=questionary.text(f'Which directory? \n>{basepath}')
        ).ask()
        dirs, files = interactive_ls(redirector, basepath + answers1["_directory"])
        current_dir = basepath + answers1["_directory"]
        choices = ['exit'] + ['..'] + ['------Directories:------'] + dirs + [
            '------Files (will be stated):------'] + files
        stop = False
        while not stop:
            answers2 = questionary.form(
                _directory=questionary.select('Whats next?', choices=choices),
            ).ask()
            log.info(f'{answers2["_directory"]}')
            if '------' in answers2["_directory"]:
                continue
            if answers2["_directory"] == 'exit':
                break
            if answers2["_directory"] != '..':
                current_dir = answers2["_directory"]
            if answers2["_directory"] == '..':
                dirs, files = interactive_ls(redirector, '/'.join(current_dir.split('/')[:-2]))
                choices = ['exit'] + ['..'] + ['------Directories:------'] + dirs + [
                    '------Files (will be stated):------'] + files
                current_dir = '/'.join(current_dir.split('/')[:-2])
                continue
            if _check_file_or_directory(redirector, answers2["_directory"]) == 'dir':
                dirs, files = interactive_ls(redirector, answers2["_directory"])
                choices = ['exit'] + ['..'] + ['------Directories:------'] + dirs + [
                    '------Files (will be stated):------'] + files
            else:
                stat(redirector, answers2["_directory"])

    ########## stat ##########
    if answers["_function"] == 'stat':
        answers1 = questionary.form(
            _directory=questionary.text(f'Which file or directory do you want to stat? \
            \n  Note: To stat the directories content, please use "stat dir". \n >{basepath}')
        ).ask()
        stat(redirector, basepath + answers1["_directory"])

    ########## stat directory ##########
    if answers["_function"] == 'stat directory':
        answers1 = questionary.form(
            _directory=questionary.text(f'Which directory do you want to stat? \n >{basepath}')
        ).ask()
        stat_dir(redirector, basepath + answers1["_directory"], True, False)

    ########## rm file ##########
    if answers["_function"] == 'rm file':
        answers1 = questionary.form(
            _filepath=questionary.text(f'Which file do you want to delete? \n >{basepath}')
        ).ask()
        del_file(redirector, basepath + answers1["_filepath"], user, ask=True)

    ########## interactive file rm ##########
    if answers["_function"] == 'interactive file rm':
        answers1 = questionary.form(
            _directory=questionary.text(f'In which directory you want to delete a file? \n>{basepath}')
        ).ask()
        dirs, files = interactive_ls(redirector, basepath + answers1["_directory"])
        current_dir = basepath + answers1["_directory"]
        choices = ['exit'] + ['..'] + ['------Directories:------'] + dirs + [
            '------Files (will be DELETED!!):------'] + files
        stop = False
        while not stop:
            answers2 = questionary.form(
                _directory=questionary.select('Which file should be DELETED next?', choices=choices),
            ).ask()
            log.info(f'{answers2["_directory"]}')
            if '------' in answers2["_directory"]:
                continue
            if answers2["_directory"] == 'exit':
                break
            if answers2["_directory"] != '..':
                current_dir = answers2["_directory"]
            if answers2["_directory"] == '..':
                dirs, files = interactive_ls(redirector, '/'.join(current_dir.split('/')[:-2]))
                choices = ['exit'] + ['..'] + ['------Directories:------'] + dirs + [
                    '------Files (will be DELETED!!):------'] + files
                current_dir = '/'.join(current_dir.split('/')[:-2])
                continue
            if _check_file_or_directory(redirector, answers2["_directory"]) == 'dir':
                dirs, files = interactive_ls(redirector, answers2["_directory"])
                choices = ['exit'] + ['..'] + ['------Directories:------'] + dirs + [
                    '------Files (will be DELETED!!):------'] + files
            else:
                # Note: answers2["_directory"] is the file in this case!
                del_file(redirector, answers2["_directory"], user, True)
                choices.remove(answers2["_directory"])

    ########## rm dir ##########
    if answers["_function"] == 'rm dir':
        answers1 = questionary.form(
            _filepath=questionary.text(f'Which directory do you want to delete? \n >{basepath}')
        ).ask()
        del_dir(redirector, basepath + answers1["_filepath"], user, ask=True)

    ########## interactive dir rm ##########
    if answers["_function"] == 'interactive dir rm':
        answers1 = questionary.form(
            _directory=questionary.text(f'In which directory you want to delete folders? \n>{basepath}')
        ).ask()
        dirs, files = interactive_ls(redirector, basepath + answers1["_directory"])
        # ask if the user wants to get the file and dir sizes before deleting
        answers2 = questionary.confirm('Do you want to determine file sizes and sort by size before deleting ?').ask()
        if answers2:
            log.info(f'Getting file and dir sizes for {len(dirs) + len(files)} elements, this may take a while...')
            choices = []
            sizes = {}
            # get file and dir sizes
            for i, dir in enumerate(dirs):
                print(f'Getting size for {i} / {len(dirs) + len(files)} element', end='\r')
                sizes[dir] = dir_size(redirector, dir, False)
                choices.append(dir)
            for i, file in enumerate(files):
                print(f'Getting size for {i + len(dirs)} / {len(dirs) + len(files)} element', end='\r')
                sizes[file] = get_file_size(redirector, file)
                choices.append(file)
            # sort by size
            choices.sort(key=lambda x: sizes[x], reverse=True)
            # now modify the choices list to add the size in front of the file/dir name
            for i in range(len(choices)):
                choices[i] = f'{_sizeof_fmt(sizes[choices[i]]) :<10} {choices[i]}'
            # add exit option to the list
            choices = ['exit'] + choices

        else:
            choices = ['exit'] + dirs + files
        # now use questionary checkbox to select the files and dirs to delete

        answers3 = questionary.checkbox('Which files and directories should be DELETED?', choices=choices).ask()
        if 'exit' in answers3:
            break
        else:
            # ask user if he want to check all files and dirs before deleting
            answers4 = questionary.confirm('[WARNING] Do you want to check all files and directories before deleting?').ask()
            if answers4:
                ask = True
            else:
                ask = False
            for selection in answers3:
                if answers2:
                    selection = selection[11:]
                log.info(f'Deleting {selection}')
                if _check_file_or_directory(redirector, selection) == 'dir':
                    del_dir(redirector, selection, user, ask, verbose=False)
                else:
                    del_file(redirector, selection, user, ask, verbose=False)



    ########## mv ##########
    if answers["_function"] == "mv":
        answers1 = questionary.form(
            _source=questionary.text(f'Which file do you want to move? \
                \n  Note: no relative paths! No overwrite! Destination has to be given explicit. \nSource: >{basepath}'
                                     ),
            _dest=questionary.text(f'\nDestination: >{basepath}'),
        ).ask()
        log.info(f'{answers1["_source"]} will be moved/renamed to {answers1["_dest"]}')
        mv(redirector, basepath + answers1["_source"], basepath + answers1["_dest"])

    ########## mkdir ##########
    if answers["_function"] == 'mkdir':
        answers1 = questionary.form(
            _filepath=questionary.text(
                f'Which directory do you want to create? (Full tree will be created!) \n >{basepath}'
            )
        ).ask()
        mkdir(redirector, basepath + answers1["_filepath"])

    ########## copy file to ##########
    if answers["_function"] == "copy file to":
        answers1 = questionary.form(
            _source=questionary.text(
                f'Which file do you want to copy to remote? Note: Complete path necessary! \nSource: >'
            ),
            _dest=questionary.text(f'Destination? Note: the path has to end with the desired filename! (/store/user/xyz/file.name) \
                    \n>{basepath}'
                                   )
        ).ask()
        log.info(f'{answers1["_source"]} will be copied to {basepath}{answers1["_dest"]}')
        copy_file_to_remote(redirector, answers1["_source"], basepath + answers1["_dest"])

    ########## copy file from ##########
    if answers["_function"] == "copy file from":
        answers1 = questionary.form(
            _source=questionary.text(f'Which file do you want to copy from remote? \
                     \nSource: >{basepath}'
                                     ),
            _dest=questionary.text(
                f'Destination? Note: the path has to end with the desired filename! (/home/user/dir/<filename.txt>) \n>'
            )
        ).ask()
        log.info(f'{answers1["_source"]} will be copied to {basepath}{answers1["_dest"]}')
        copy_file_from_remote(redirector, basepath + answers1["_source"], answers1["_dest"])

    ########## dir size ##########
    if answers["_function"] == 'dir size':
        answers1 = questionary.form(
            _filepath=questionary.text(f'Which directory? \n >{basepath}'
                                       )
        ).ask()
        dir_size(redirector, basepath + answers1["_filepath"], True)

    ########## dir content ##########
    if answers["_function"] == 'dir content':
        answers1 = questionary.form(
            _directory=questionary.text(f'Show content of which folder \n>{basepath}')
        ).ask()
        dirs, files = interactive_ls(redirector, basepath + answers1["_directory"])
        # now get the size of all files and dirs
        for dir in dirs:
            size = dir_size(redirector, dir, False)
            log.info(f'{_sizeof_fmt(size) :<10} {dir}')
        for file in files:
            size = get_file_size(redirector, file)
            log.info(f'{_sizeof_fmt(size) :<10} {file}')




    ########## create file list ##########
    if answers["_function"] == 'create file list':
        answers1 = questionary.form(
            _filepath=questionary.text(f'Which directory? \n >{basepath}'
                                       )
        ).ask()
        answers2 = questionary.form(
            exclude=questionary.text(f'Do you want to exclude fils (e.g. ".log") [Enter to continue]? \n >')
        ).ask()
        create_file_list(redirector, basepath + answers1["_filepath"], answers2["exclude"])

    ########## change base path ##########
    if answers["_function"] == 'change base path':
        basepath = str(input('Which basepath you want to use (default: /store/user/)?'))
        log.info(f'Selected base path: {basepath}')
        if basepath[0] != '/' or basepath[-1] != '/':
            exit('The base path has to begin and end with a "/"!')
        log.debug(f'[DEBUG] {redirector}, {basepath}')
        stat_dir(redirector, basepath, False, False)  # check, if dir exists
        log.info(f'Base path set to {basepath}')

    ########## change redirector ##########
    if answers["_function"] == 'change redirector':
        log.info(f'current redirector: {redirector}')
        answers1 = questionary.form(
            _redirector=questionary.select('Which redirector you want to use?',
                                           choices=[
                                               'root://cmsxrootd-redirectors.gridka.de:1094/, (RO)',
                                               'root://cmsxrootd-kit.gridka.de:1094/, (RW)',
                                               'root://xrootd-cms.infn.it:1094/, EU redirector',
                                               'root://cmsxrootd.fnal.gov:1094/, US redirector',
                                               'root://cms-xrd-global.cern.ch:1094/, global redirector',
                                               'other'
                                           ])
        ).ask()
        if answers1["_redirector"] == 'other':
            redirector = str(input('Which redirector you want to use?'))
            if len(redirector) == 0:
                exit('No redirector specified!')
        else:
            redirector = answers1["_redirector"].split(',')[0]
        log.info(f'Redirector changed to {redirector}')
        redirector_type = _check_redirector(redirector)  # not supported from dcache door
        log.info(f'Redirector type: {redirector_type}')

    ########## help  ##########
    if answers["_function"] == 'help':
        help_dict = {
            '<exit>': 'exit the script',
            '<help>': 'print this help',
            '<ls>': 'static ls on a fixed directory',
            '<interactive ls>': 'interactive ls through the energy FTW!',
            '<stat>': 'xrdfs stat on file or directory',
            '<stat directory>': 'xrdfs stat on directory content',
            '<dir size>': 'prints the size of the directory. With DEBUG: gives sizes of sub-dirs',
            '<rm file>': 'remove a file from remote',
            '<interactive file rm>': 'select a file on CLI to remove',
            '<rm dir>': 'remove a directory on remote',
            '<mv>': 'move or rename a file/directory; paths need to be explicit!',
            '<mkdir>': 'xrdfs mkdir; full tree creation enabled',
            '<copy file to>': 'copy a file to remote',
            '<copy file from>': 'copy a file from remote',
            '<change base path>': 'changing the base path for convenience',
            '<change redirector>': 'change the redirector',
            '<create file list>': 'write out file list of given directory'
        }
        print('#####################################')
        print('# General notes and recommendations #')
        print('#####################################')
        print('First of all: ---BE CAREFUL!---')
        print('   Like xrdfs rm/gfal-rm, there is no real user access management! \
                \n   You can potentially delete everything...'
              )

        print('###################################################')
        print('-----------------------------------------------')
        for key, val in help_dict.items():
            print(key, ': ', val)
            print('-----------------------------------------------')
        print('###################################################')
