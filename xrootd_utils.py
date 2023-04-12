import logging
from typing import Tuple, Dict, Any, List
# import argparse


from XRootD import client
from XRootD.client.flags import DirListFlags, OpenFlags, MkDirFlags, QueryCode

##################################
# Comment in for CLI usage without argparse
##################################
# redirector = 'root://cmsxrootd-kit.gridka.de/'
# user = <username> in /store/<username>
##################################

""" #### for the standalone version with cli arguments, comment in:
parser = argparse.ArgumentParser(
                    description = 'xrootd python bindings for dummies')
parser.add_argument('-r', '--redirector', help='root://xrd-redirector:1094/', required=True)
parser.add_argument('-u', '--user', help='cms username', required=True)
parser.add_argument('-l', '--loglevel', help='python loglevel={"INFO", "VERBOSE", "DEBUG"}', default='INFO')
args = vars(parser.parse_args())

##################################################
redirector = args["redirector"]  # '<redirector>'
user = args["user"]  # '<username>'
loglevel = args["loglevel"]
##################################################
"""

########## logging ###############
loglevel = 'INFO'

FORMAT = '%(message)s'
logging.basicConfig(format=FORMAT)
log = logging.getLogger()
log.setLevel(loglevel)

#################### Flags ######################
#  /xrootd/bindings/python/libs/client/flags.py #
#################################################
StatInfoFlags = {
    'X_BIT_SET': 1,               # 1
    'IS_DIR': 2,                 # 10
    'OTHER': 4,                 # 100
    'OFFLINE': 8,              # 1000
    'IS_READABLE': 16,        # 10000
    'IS_WRITABLE': 32,       # 100000
    'POSC_PENDING': 64,     # 1000000
    'BACKUP_EXISTS': 128,  # 10000000
}


def _print_flags(inp_flag: int, StatInfoFlags: dict) -> None:
    """
    Function to print out the status bits of a file or directory.
    Note: only prints in DEBUG mode to reduce spam!

    Parameters
    ----------
    inp_flag      : int
    StatInfoFlags : str

    Returns
    -------
    None
    """
    log.debug('[DEBUG] Status flags:')
    rev_flag = bin(inp_flag)[2:][::-1]  # reverse order of inp_flag (excl. 0b) for printing
    while len(rev_flag) < 8:  # fill with 0 for printing
        rev_flag += '0'
    for n, flag in enumerate(StatInfoFlags.keys()):
        tmp = rev_flag[n]
        log.debug(f'{rev_flag[n]} {flag}')
    log.debug('-------------------------------------')
#################################################


############# helper functions ##################
def _check_redirector(redirector: str) -> str:
    """
    Function to check the type of <redirector>.
    Note: The behaviour of some bindings change
      based on the redirector type!

    Parameters
    ----------
    redirector : str

    Returns
    -------
    redir_type : str
        normal, dcache, fatal, unknown
    """
    redir_type: str

    status, _ = client.FileSystem(redirector).ping()
    log.debug(f'[DEBUG][check_redirector] status: {status}')
    if status.ok:
        redir_type = 'normal'  # normal xrd redirector
    else:
        if 'fatal' in status.message.lower():
            redir_type = 'fatal'
            log.critical('[CRITICAL][check_redirector] No valid redirector!')
        elif 'error' in status.message.lower():
            redir_type = 'dcache'  # dcache door / else
        else:  # should not happen
            redir_type = 'unknown'
            log.critical('[CRITICAL][check_redirector] Unknown redirector type. Exiting...')
    return redir_type


def _check_file_or_directory(redirector: str, input_path: str) -> str:
    """
    Helper function to check if <input_path> is a file or a
    directory by checking the statinfo.flags.

    Parameters
    ----------
    redirector  : str
    input_path  : str

    Returns
    -------
    _type       : str
        "dir" for directories, "file" for files, "err" for error
    """
    myclient = client.FileSystem(redirector)
    status, listing = myclient.stat(input_path, DirListFlags.STAT)  # use .stat!
    log.debug(f'[DEBUG][check_file_or_directory] status: {status}, listing: {listing}, path: {input_path}')

    if not status.ok:
        log.critical('[CRITICAL][_check_file_or_directory] File or directory does not exist')
        return 'err'
    # bit comparison with IS_DIR flag:
    if listing.flags & StatInfoFlags["IS_DIR"]:
        return 'dir'
    else:
        return 'file'


def _sizeof_fmt(num, suffix="B"):  # https://github.com/gengwg/Python/blob/master/sizeof_fmt.py
    """
    Function to convert units.

    Parameters
    ----------
    num     : int
    suffix  : str

    Returns
    -------
        size in desired format
    """
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1000.0:
            return f"{num:> 6.1f} {unit}{suffix}"
        num /= 1000.0
    return f"{num:.1f} Yi{suffix}"


def _get_directory_listing(redirector: str, directory: str) -> Tuple[Dict[str, int], Any]:
    """
    Returns the files and directories within a directory as a dict.

    Parameters
    ----------
    redirector : str
    directory  : str

    Returns
    -------
    (dict, object)
        contains the full directory listing (dirs and files) and the xrd output
    """
    dir_dict = {}
    myclient = client.FileSystem(redirector)
    status, listing = myclient.dirlist(directory, DirListFlags.STAT)
    log.debug(f'[DEBUG][_get_directory_listing] status: {status}, listing: {listing}, directory: {directory}')

    if not status.ok:
        log.critical(f'[CRITICAL][_get_directory_listing] Status: {status.message}')
    if listing is None:
        log.critical('[CRITICAL][_get_directory_listing] No directory given or query failed.')
        return dir_dict, None  # return empty

    for entry in listing:
        log.debug(f'[DEBUG][get_directory_listing] Info: {entry}')
        if entry.statinfo.flags & StatInfoFlags["IS_DIR"]:
            dir_dict[f"{listing.parent + entry.name}/"] = 1
        else:
            dir_dict[f"{listing.parent + entry.name}"] = 0
    return dir_dict, listing


def _get_file_list(dir_dict: dict) -> List:
    """
    Helper function to extract the files from a listing.

    Parameters
    ----------
    dir_dict : dict
        contains the full directory listing (dirs and files)

    Returns
    -------
    list
        list of files
    """
    return [k for k, v in dir_dict.items() if v == 0]


def _get_dir_list(dir_dict: dict) -> List:
    """
    Helper function to extract the directories from a listing.

    Parameters
    ----------
    dir_dict : dict
        contains the full directory listing (dirs and files)

    Returns
    -------
    list
        list of directories
    """
    return [k for k, v in dir_dict.items() if v == 1]


def _get_file_size(redirector: str, file: str) -> int:
    """
    Returns the file size, calculated by the stat function.
    To prevent spam, the file size is only listed on DEBUG loglevel.

    Parameters
    ----------
    redirector  : str
    file        : str

    Returns
    -------
    int
        file size in Byte, -999 for error
    """
    myclient = client.FileSystem(redirector)
    status, listing = myclient.stat(file, DirListFlags.STAT)  # use FS.stat!
    log.debug(f'[DEBUG][_get_file_size] status: {status}, listing: {listing}, file: {file}')

    # check if file or dir exists
    if not status.ok:
        log.critical(f'[CRITICAL][_get_file_size] The file or directory does not exist!')
        return -999
    return listing.size


def _get_dir_size(redirector: str, directory: str, show_output=True, acc_size=0) -> int:
    """
    Returns the directory size, calculated by the stat_dir function.
    To prevent spam, the subdirectories with sizes are only listed on DEBUG loglevel.

    Parameters
    ----------
    redirector  : str
    directory   : str
    show_output : bool

    Returns
    -------
    int
        directory size in Byte, -999 for error
    """
    dirsize = stat_dir(redirector, directory, False, True)  # don't show output, get size
    if dirsize == -999:
        log.critical(f'[CRITICAL][_get_dir_size] stat dir failed.')
        return -999
    GiB = dirsize / (1 << 30)
    log.debug(f'[DEBUG] Directory size of {directory}: GiB: {GiB}')
    if show_output:
        log.info(f'Byte: {dirsize} (GiB: {GiB}G)')
    return dirsize

###########################################


def stat(redirector: str, input_path: str) -> None:
    """
    xrdfs stat on <file>.
    Note: In general, there are two ways to stat: FileSystem.stat
    Here, we actually use the stat_dir function, since the file stat is buggy in the xrd
    bindings...

    Note: for full flag output use "stat" in DEBUG mode!

    Parameters
    ----------
    redirector : str
    input_path : str

    Returns
    -------
    None
    """
    myclient = client.FileSystem(redirector)
    status, listing = myclient.stat(input_path, DirListFlags.STAT)  # use FS.stat!
    log.debug(f'[DEBUG][stat] status: {status}, listing: {listing}, input_path: {input_path}')

    if not status.ok:
        log.critical(f'[CRITICAL][stat] The file or directory does not exist!')
        return None

    log.info('-------------------------------------')
    log.info(f'name: {input_path}')
    log.info(f'id: {listing.id}\n (++++ Note: ID is broken with the python bindings. Please use xrdfs stat ++++)')
    log.info(f'size: {listing.size}')
    log.info(f'flags: {listing.flags}')
    log.info(f'modtimestr: {listing.modtimestr}')
    log.info('-------------------------------------')

    # verbose stat:
    _print_flags(listing.flags, StatInfoFlags)
    return None


def stat_dir(redirector: str, directory: str, show_output=True, get_size=False) -> int:
    """
    xrdfs binding for stat on <directory>.
    It is also used as helper hunction for getting the directory size.

    Parameters
    ----------
    redirector  : str
    directory   : str
    show_output : bool
    get_size    : bool

    Returns
    -------
    int
        directory size if get_size=True, else 0 ,-999 for error
    """
    myclient = client.FileSystem(redirector)
    status, listing = myclient.dirlist(directory, DirListFlags.STAT)
    log.debug(f'[DEBUG][stat_dir] status: {status}, listing: {listing}, directory: {directory}, '
              f'show_output: {show_output}, get_size: {get_size}')

    if not status.ok:
        log.critical(f'[CRITICAL][stat dir] Failed.')
        return -999

    dirsize = 0

    if show_output:
        for entry in listing:
            print('-------------------------------------')
            print('name: ', entry.name)
            print('id: ', entry.statinfo.id)
            print('size: ', entry.statinfo.size)
            print('flags: ', entry.statinfo.flags)
            print('modtimestr: ', entry.statinfo.modtimestr)
        print('-------------------------------------')

        log.debug(f'[DEBUG][stat dir] full output: {listing},\nstatus: {status}')

    if get_size:
        for entry in listing:
            if entry.statinfo.flags & StatInfoFlags["IS_DIR"]:
                dirsize += _get_dir_size(redirector, listing.parent + entry.name, False)
            else:
                dirsize += entry.statinfo.size
    return dirsize


def ls(redirector: str, input_path: str) -> None:
    """
    xrdfs ls

    ATTENTION: The behaviour depends on the redirector you are using.

    Parameters
    ----------
    redirector : str
    input_path : str

    Returns
    -------
    None
    """
    # check, if <directory> is a file. If yes, just print the path (like xrdfs ls)
    _type = _check_file_or_directory(redirector, input_path)
    if _type == 'err':
        log.debug('[DEBUG][ls] _check_file_or_directory failed.')
        return None
    elif _type == 'file':
        log.info(f'{input_path}')
        return None

    _, listing = _get_directory_listing(redirector, input_path)
    if listing is None:
        log.debug('[DEBUG][ls] _get_directory_listing failed.')
        return None

    log.info(f'{listing.parent}, N: {listing.size}')
    for entry in listing:
        if entry.statinfo.flags & StatInfoFlags["IS_DIR"]:
            _file_or_dir = '(dir)'
        else:
            _file_or_dir = '(file)'
        log.info('{0} {1:>10} {2} {3}'.format(
            entry.statinfo.modtimestr, entry.statinfo.size, entry.name, _file_or_dir)
        )
    return None


def interactive_ls(redirector: str, directory: str) -> Tuple[List, List]:
    dir_dict, listing = _get_directory_listing(redirector, directory)
    dirs = []
    files = []
    if listing is None:
        log.critical('[CRITICAL][interactive ls] _get_directory_listing failed.')
        return dirs, files  # in case of ERROR, the interactive lists are empty
    dirs = _get_dir_list(dir_dict)
    files = _get_file_list(dir_dict)
    return dirs, files


def copy_file_to_remote(redirector: str, source: str, dest: str) -> None:
    """
    xrdcp implementation to copy a local file to remote
    To overwrite the target file, force has to be set to True
    NOTE: the paths has to be exactly as implemented, else it doesn't work!
    e.g.:
      source '/home/<user>/xrdexample/test.txt'
      dest: 'root://<redirector>:1094//store/<user>/test.txt'
      Caution: The filename has to be within the dest path! A dir only is not sufficient!

    Parameters
    ----------
    redirector : str
    source     : str
    dest       : str

    Returns
    -------
    None
    """
    myclient = client.FileSystem(redirector)
    status, _ = myclient.copy('file://' + source, redirector + dest, force=False)  # force: overwrite target!
    log.debug(f'[DEBUG][copy to] Status: {status}, source: {source}, dest: {dest}')

    if not status.ok:
        log.critical(f'[CRITICAL] Failed.')
        return None
    log.info(f'File {source} copied to {dest}.')
    return None


def copy_file_from_remote(redirector: str, remote_source: str, dest: str) -> None:
    """
    xrdcp implementation to copy a remote file to local
    NOTE: the paths has to be exactly as implemented, else it doesn't work!
    e.g.:
      source: 'root://<redirector>:1094//store/<user>/test.txt'
      dest: '/home/<user>/xrdexample/test.txt'
      Caution: The filename has to be within the dest path! A target dir only is not sufficient!

    Parameters
    ----------
    redirector    : str
    remote_source : str
    dest          : str

    Returns
    -------
    None
    """
    myclient = client.FileSystem(redirector)
    status, _ = myclient.copy(redirector + remote_source, 'file://' + dest, force=False)
    log.debug(f'[DEBUG][copy from] Status: {status.message}, remote_source: {remote_source}, dest: {dest}')

    if not status.ok:
        log.critical(f'[CRITICAL] Failed.')
        return None

    log.info(f'File {remote_source} copied to {dest}.')
    return None


def del_file(redirector: str, filepath: str, user: str, ask=True, verbose=True) -> None:
    """
    Function to delete files from remote.
    Note: you have to specify the RW redirector!

    Parameters
    ----------
    redirector : str
    filepath   : str
    user       : str
    ask        : bool
    verbose    : bool

    Returns
    -------
    None
    """
    myclient = client.FileSystem(redirector)
    to_be_deleted = redirector + filepath

    # for security reasons... If you want to delete something else, comment this out
    if user in filepath:
        log.debug(f'[DEBUG] {user} tries to delete {filepath}')
    else:
        log.critical('[CRITICAL] Permission denied. Your username was not found in the filepath!')
        return None

    if ask:
        if verbose:
            log.info(f'The following file will be deleted: {filepath}')
        stat(redirector, filepath)
    if ask:
        if str(input(f"Are you sure to delete <{to_be_deleted}>? ")) == 'y':
            status, _ = myclient.rm(filepath)
            log.debug(f'[DEBUG][rm] Status: {status}, filepath: {filepath}, user: {user}, ask: {ask}, verbose: {verbose}')
            if not status.ok:
                log.critical(f'[CRITICAL] Failed.')
                return None
        else:
            log.critical("[CRITICAL] Aborted.")
            return None
    else:
        status, _ = myclient.rm(filepath)
        log.debug(f'[DEBUG][rm] Status: {status}, filepath: {filepath}, user: {user}, ask: {ask}, verbose: {verbose}')
        if not status.ok:
            log.critical(f'[CRITICAL] Failed.')
            return None
    if verbose:
        log.info(f'file: {filepath} removed.')
    return None


def del_dir(redirector: str, directory: str, user: str, ask=True, verbose=True) -> None:
    """
    Function to delete a directory.
    There is no recursive way available (or enabled) in xrootd.
    Therefore, looping over all files and removing them is the only way...

    Parameters
    ----------
    redirector : str
    directory  : str
    user       : str
    ask        : bool
    verbose    : bool

    Returns
    -------
    None
    """
    if user in directory:
        log.debug(f'[DEBUG] {user} tries to delete {directory}')
    else:
        log.critical('[CRITICAL] Permission denied. Your username was not found in the directory path!')
        return None

    myclient = client.FileSystem(redirector)
    status, listing = myclient.dirlist(directory, DirListFlags.STAT)
    log.debug(f'[DEBUG][rm dir] Status: {status}, directory: {directory}, user: {user}, ask: {ask}, verbose: {verbose}')

    if not status.ok:
        log.critical(f'Failed. Status: {status.message}')
        return None
    if verbose:
        log.info(f'The following files will be deleted within {directory}:')
        ls(redirector, directory)  # list the directory content that will be deleted
    if ask:
        if str(reply := input(f'Are you sure to delete the following directory: {directory}? (y/n/all) ')) == 'y':
            log.info("Will delete with ask=True")
            ask = True
        elif reply == 'all':
            log.info("Will delete with ask=False")
            ask = False
        elif reply == 'n':
            log.info('Nothing deleted.')
            return None
        else:
            log.critical('[CRITICAL] Failed.')
            return None

    for file in listing:
        log.debug(f'[DEBUG] {redirector}{listing.parent}{file.name}')
        if file.statinfo.flags & StatInfoFlags["IS_DIR"]:  # check if "file" is a directory -> delete recursively
            log.debug(f'[DEBUG][rm dir] list entry: {file}')
            del_dir(redirector, listing.parent + file.name, user, ask, verbose)
        else:
            del_file(redirector, listing.parent + file.name, user, False, verbose)

    status, _ = myclient.rmdir(directory)  # when empty, remove empty dir
    log.debug(f'[DEBUG][rm dir] rm status: {status}')
    if not status.ok:
        log.critical(f'Failed. Status: {status.message}')
        return None
    if verbose:
        log.info('Directory removed.')
    return None


def mv(redirector: str, source: str, dest: str) -> None:
    """
    xrdfs mv. Can be used to rename or move files or directories.
    If you want to move a directory into another, you have to
    give the path explicitly:
        mv dir1 into dir2 : mv /path_to_dir1/dir1 /path_to_dir2/dir2/dir
    Note: No overwrite (files and dirs)!

    Parameters
    ----------
    redirector : str
    source     : str
    dest       : str

    Returns
    -------
    None
    """
    myclient = client.FileSystem(redirector)
    log.info(f'mv: {source} to {dest}')
    status, _ = myclient.mv(source, dest)
    log.debug(f'[DEBUG][mv] Status: {status}, source: {source}, dest: {dest}')

    if not status.ok:
        log.critical(f'[CRITICAL] Failed')
        return None
    log.info('File or directory moved.')
    return None


def mkdir(redirector: str, directory: str) -> None:
    """
    xrdfs mkdir "-p" (recursive, creates the entire tree)

    Parameters
    ----------
    redirector : str
    directory  : str

    Returns
    -------
    None
    """
    myclient = client.FileSystem(redirector)
    status, _ = myclient.mkdir(directory, MkDirFlags.MAKEPATH)
    log.debug(f'[DEBUG][mkdir] Status: {status}, directory: {directory}')

    if not status.ok:
        log.critical(f'[CRITICAL] Failed.')
        return None
    log.info(f'{directory} created.')
    return None


def locate(redirector: str, filepath: str) -> bool:
    """
    Function to check whether a file can be served by the redirector.

    Parameters
    ----------
    redirector : str
    filepath   : str

    Returns
    -------
    bool
    """
    myclient = client.FileSystem(redirector)
    status, locations = myclient.locate(filepath, OpenFlags.REFRESH)
    log.debug(f'[DEBUG][locate] Status: {status}, filepath: {filepath}')

    if not status.ok:
        log.critical(f'[CRITICAL] Failed.')
        return False  # file cannot be located
    log.info(locations)
    return True


def create_file_list(redirector: str, directory: str, exclude: str) -> None:
    """
    Function to create the file list of a directory and write it to file. Certain files can be excluded with "exclude".
    Note: if directories are present within the directory, they will be written as well.

    Parameters
    ----------
    redirector : str
    directory  : str
    exclude    : str
        file type ending to be excluded

    Returns
    -------
    None
    """
    log.debug(f'[DEBUG][create file list] directory: {directory}, exclude: {exclude}')
    dir_dict, _ = _get_directory_listing(redirector, directory)
    dir_str = directory.replace('/', '_')
    output_name = f'list{dir_str}.txt'
    warn = False
    with open(output_name, 'w') as filelist:
        for entry, v in dir_dict.items():
            if len(exclude) > 0 and exclude in entry:
                log.debug(f'[DEBUG][create file list] {entry} excluded.')
                continue
            if v == 1:
                warn = True
            filelist.write(entry + '\n')
    if warn:
        log.warning('+++ Warning +++ There are directories listed in your filelist')
    log.info(f'{output_name} created.')
    # log.debug(f'content: {dir_dict}') # spam
    return None

########################## Examples #############################
# If you do not want to use the interactive (questionary) mode, #
# the utility functions can be used separately. The following   #
# functions are available in standalone mode.                   #                                                  #
#################################################################
# the redirector is hardcoded in the functions to prevent file prefix errors (especially with all the "/")

# ls
# ls(redirector, full_path_to_file_or_dir)

# stat file or direcectory
# stat(redirector, full_path_to_file_or_dir)

# stat directory
# stat_dir(redirector, full_path_to_dir, show_output=True, get_size=False)

# dir size
# dir_size(redirector, full_path_to_dir, show_output=True)

# delete a file
# del_file(redirector, '/store/user/<username>/<path>/file_to_be_deleted.txt', user='<username>', ask=True)

# delete all files and the directory
# del_dir(redirector, '/store/user/<username>/<path_to_be_deleted>', user='<username>', ask=True)

# mv
# mv(redirector, '/store/user/<username>/<path>/file.txt', /store/user/<username>/<new_path>/file.txt')

# copy to remote
# Note: the filename has to be given in the destination path!
# copy_file_to_remote(redirector, '/home/<user>/file.txt', '/store/user/<username>/<dir>/file.txt')

# copy from remote
# Note: the filename has to be given in the destination path!
# copy_file_from_remote(redirector, '/store/user//<username>/<dir>/file.txt', '/home/<user>/<dir>/file.txt')

# mkdir
# mkdir(redirector, full_path_to_dir/<newdir_name>')  # full path is created (<=> -p)

# create filelist
# create_file_list(redirector, full_path_to_dir, exclude='.log')
