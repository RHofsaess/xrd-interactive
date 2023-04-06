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
StatInfoFlags = {
  'X_BIT_SET'     : 1,   #        1
  'IS_DIR'        : 2,   #       10
  'OTHER'         : 4,   #      100
  'OFFLINE'       : 8,   #     1000
  'IS_READABLE'   : 16,  #    10000
  'IS_WRITABLE'   : 32,  #   100000
  'POSC_PENDING'  : 64,  #  1000000
  'BACKUP_EXISTS' : 128, # 10000000
}

def _print_flags(inp_flag: int, StatInfoFlags: dict) -> None:
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
def _check_redirector(redirector: str) -> None:
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
        normal, dcache
    """
    redir_type : str

    status, _ = client.FileSystem(redirector).ping()
    if status.ok:
        redir_type = 'normal'  # normal xrd redirector
    else:
        if 'fatal' in status.message.lower():
            exit('No valid redirector!')
        elif 'error' in status.message.lower():
            redir_type = 'dcache'  # dcache door / else
        else:
            exit('Unknown redirector type. Exiting...')
    log.debug(f'[DEBUG][check_redirector] status: {status}')
    return redir_type


def _check_file_or_directory(redirector: str, input_path: str) -> str:
    """
    Helper function to check if <input_path> is a file or a
    directory by checking the statinfo.flags.

    +++ Attention +++
    The directory flag for FileSystem.stat differs
    from the directory flag returned by FileSystem.dirlist.
    Here, we only use the >>.stat<< flags!

    Parameters
    ----------
    redirector  : str
    input_path  : str

    Returns
    -------
    _type       : str
        "dir" for directories, "file" for files
    """
    myclient = client.FileSystem(redirector)
    status, listing = myclient.stat(input_path, DirListFlags.STAT)  # use .stat!
    log.debug(f'[DEBUG][check_file_or_directory] status: {status}, listing: {listing}, path: {input_path}')

    if not status.ok:
        exit('file or directory does not exist!')
    # check IS_DIR flag:
    if listing.flags & StatInfoFlags["IS_DIR"]:
        return 'dir'
    else:
        return 'file'


############## ---deprecated--- ###############
''' # This is kept as an example on how to handle files on file level
def _is_file(redirector: str, filepath: str) -> bool:
    """
    Helper function to verify that <filepath> exists and is a file.
    If yes, nothing happens, if not, an error is raised.
    Note: implementation not used anymore, since the File.stat() is buggy...

    Parameters
    ----------
    redirector  : str
    filepath    : str

    Returns
    -------
    bool
    """


    # This sometimes takes forever, therefore, it is exchanged as the opposite of "_is_directory" :D
    with client.File() as f:
        f.open(redirector + filepath, OpenFlags.READ)
        try:
            status, stat = f.stat()
            if not status.ok:
                if show_output:
                    log.critical(f'Status: {status.message}')
            else:
                _is_f = True
        except ValueError as e:
            _is_f = False
            if show_output:
                log.critical('File open error. Correct path? May try ls(filepath) before.')
                log.critical(f'Exception: {e}')
                log.debug(f'[DEBUG] {_is_f}')
    return _is_f
'''
###############################################


def _get_directory_listing(redirector: str, directory: str) -> Tuple[Dict[str, int], Any]:
    """
    Returns the files and directories within a directory as a dict.
    Note: A small workaround is used for the type check to spare the storage servers

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
    log.debug(f'[DEBUG][get_directory_listing] Status: {status.message}')
    if not status.ok:
        log.critical(f'[get_directory_listing] Status: {status.message}')
    assert status.ok  # directory or redirector faulty

    for entry in listing:
        #####################################################################################
        # the correct way would be to check each file:                                      #
        # if _check_file_or_directory(redirector, listing.parent + entry.name) == 'file':   #
        #    dir_listing[f"{listing.parent + entry.name}"] = 0                              #
        # elif _check_file_or_directory(redirector, listing.parent + entry.name) == 'dir':  #
        #    dir_listing[f"{listing.parent + entry.name}"] = 1                              #
        #####################################################################################
        # faster way to check if file or dir: less DDOS with only one query
        if entry.statinfo.flags == 51 or entry.statinfo.flags == 19:
            # directories have a size of 512
            assert (entry.statinfo.size == 512)  # just to make sure for the recursive stuff
            dir_dict[f"{listing.parent + entry.name}/"] = 1
        elif entry.statinfo.flags == 48 or entry.statinfo.flags == 16:
            dir_dict[f"{listing.parent + entry.name}"] = 0
        else:
            log.debug(f'[DEBUG][get_directory_listing] Info: {entry}')
            exit("Unknown flags. RO files, strange permissions?")
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


def _sizeof_fmt(num, suffix="B"):  # https://github.com/gengwg/Python/blob/master/sizeof_fmt.py
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1000.0:
            return f"{num:> 6.1f} {unit}{suffix}"
        num /= 1000.0
    return f"{num:.1f} Yi{suffix}"

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

    if not status.ok:
        log.debug(f'[DEBUG][stat] Status: {status}')
        log.info('The file or directory does not exist!')
        return None

    log.debug(f'[DEBUG][stat] status: {status}, listing: {listing}, {input_path}')
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
    xrdfs binding for stat on <directory>

    Parameters
    ----------
    redirector  : str
    directory   : str
    show_output : bool
    get_size    : bool

    Returns
    -------
    int
        directory size if get_size=True, else 0
    """

    myclient = client.FileSystem(redirector)
    status, listing = myclient.dirlist(directory, DirListFlags.STAT)
    if not status.ok:
        log.critical(f'[stat dir] Status: {status.message}')
    assert status.ok  # stat on dir failed, does the dir exist?

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
            if entry.statinfo.size == 512:
                assert (entry.statinfo.flags == 51 or entry.statinfo.flags == 19)  # make sure it's a directory
                dirsize += dir_size(redirector, listing.parent + entry.name, False)
            else:
                dirsize += entry.statinfo.size
    return dirsize


def get_file_size(redirector: str, file: str) -> int:
    """
    Returns the file size, calculated by the stat function.
    To prevent spam, the file size is only listed on DEBUG loglevel.

    Parameters
    ----------
    redirector  : str
    file        : str
    show_output : bool

    Returns
    -------
    int
        file size in Byte
    """
    myclient = client.FileSystem(redirector)
    status, listing = myclient.stat(file, DirListFlags.STAT)  # use FS.stat!

    # check if file or dir exists
    if not status.ok:
        log.debug(f'[DEBUG][stat] Status: {status}')
        log.info('The file or directory does not exist!')
        return None

    return listing.size

def dir_size(redirector: str, directory: str, show_output=True, acc_size=0) -> int:
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
        directory size in Byte
    """
    dirsize = stat_dir(redirector, directory, False, True)  # don't show output, get size
    GiB = dirsize / (1 << 30)
    log.debug(f'[DEBUG] Directory size of {directory}: GiB: {GiB}')
    if show_output:
        log.info(f'Byte: {dirsize} (GiB: {GiB}G)')
    return dirsize


def ls(redirector: str, input_path: str) -> None:
    """
    xrdfs ls: the exact behavior is mirrored
    Note: when a filepath is appended with a '/', it is stated anyway
    This behaviour is according to xrdfs ls...
    (example: /store/user/testdir/testfile.txt/ works as well)

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
    if _check_file_or_directory(redirector, input_path) == 'file':
        log.info(f'{input_path}')
        return None

    _, listing = _get_directory_listing(redirector, input_path)

    log.info(f'{listing.parent}, N: {listing.size}')
    for entry in listing:
        # different way to check if dir or file (see above)
        if entry.statinfo.size == 512 and '.' not in entry.name:
            _is_dir = '(dir)'
        elif entry.statinfo.size == 512 and '.' in entry.name:
            _is_dir = '(dir) [TO BE REVIEWED BECAUSE OF "."]'
            log.debug(f'[DEBUG][ls] entry: {entry}')
            assert (entry.statinfo.flags == 51 or entry.statinfo.flags == 19)  # to make sure it is a directory; evtl wrong permissions?
        else:
            _is_dir = '(file)'
        log.info('{0} {1:>10} {2} {3}'.format(
            entry.statinfo.modtimestr, entry.statinfo.size, entry.name, _is_dir)
        )
    return None


def interactive_ls(redirector: str, directory: str) -> Tuple[List, List]:
    dir_dict, listing = _get_directory_listing(redirector, directory)
    dirs = list(_get_dir_list(dir_dict))  # convert to list for type hints...
    files = list(_get_file_list(dir_dict))  # convert to list for type hints...
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
    log.debug(f'[DEBUG][copy to] Status: {status}')
    if not status.ok:
        log.critical(f'Status: {status.message}')
    assert status.ok  # forgot filename on dest, file exists, or RO redirector?

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
    log.debug(f'[DEBUG][copy from] Status: {status}')
    if not status.ok:
        log.critical(f'Status: {status.message}')
    assert status.ok

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
        log.critical('Permission denied. Your username was not found in the filepath!')
        exit(-1)

    if ask:
        if verbose:
            log.info(f'The following file will be deleted: {filepath}')
        stat(redirector, filepath)
    if ask:
        if str(input(f"Are you sure to delete <{to_be_deleted}>? ")) == 'y':
            status, _ = myclient.rm(filepath)
            log.debug(f'[DEBUG][rm] Status: {status}')
            if not status.ok:
                log.critical(f'Status: {status.message}')
            assert status.ok  # file deletion failed; RO redirector?
        else:
            log.critical("failed.")
            return None
    else:
        status, _ = myclient.rm(filepath)
        log.debug(f'[DEBUG][rm] Status: {status}')
        if not status.ok:
            log.critical(f'Status: {status.message}')
        assert status.ok  # file deletion failed
    if verbose:
        log.info(f'file: {filepath} removed.')
    return None


def del_dir(redirector: str, directory: str, user: str, ask=True, verbose=True) -> None:
    """
    Function to delete a directory.
    There is no recursive way available (or enabled) in xrootd.
    Therefore, looping over all files and removeing them is the only way...

    Parameters
    ----------
    redirector : str
    directory  : str
    user       : str
    ask        : bool

    Returns
    -------
    None
    """
    if user in directory:
        log.debug(f'[DEBUG] {user} tries to delete {directory}')
    else:
        log.critical('Permission denied. Your username was not found in the directory path!')
        exit(-1)

    myclient = client.FileSystem(redirector)
    status, listing = myclient.dirlist(directory, DirListFlags.STAT)
    log.debug(f'[DEBUG][rm dir] Status: {status}')
    if not status.ok:
        log.critical(f'Status: {status.message}')
    assert status.ok  # directory does not exists
    if verbose:
        log.info(f'The following files will be deleted within {directory}:')
        ls(redirector, directory)  # list the directory content that will be deleted
    if ask:
        if str(reply:=input(f'Are you sure to delete the following directory: {directory}? (y/n/all) ')) == 'y':
            log.info("Will delete with ask=True")
            ask = True
        elif reply == 'all':
            log.info("Will delete with ask=False")
            ask = False
        elif reply == 'n':
            log.info('Nothing deleted.')
            return None
        else:
            log.critical('failed.')
            return None
    for file in listing:  # unfortunately, there is no recursive way in xrd...
        log.debug(f'[DEBUG] {redirector}{listing.parent}{file.name}')
        if file.statinfo.size == 512:  # check if "file" is a directory -> delete recursively
            log.debug(f'[DEBUG][rm dir] list entry: {file}')
            assert (file.statinfo.flags == 51 or file.statinfo.flags == 19)  # make sure it is a directory; evtl wrong permissions?
            del_dir(redirector, listing.parent + file.name, user, ask, verbose)
        else:
            del_file(redirector, listing.parent + file.name, user, False, verbose)

    status, _ = myclient.rmdir(directory)  # when empty, remove empty dir
    log.debug(f'[DEBUG][rm dir] rm status: {status}')
    if not status.ok:
        log.critical(f'Status: {status.message}')
    assert status.ok  # dir removal failed: check path or redirector
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
    log.debug(f'[DEBUG][mv] Status: {status}')
    if not status.ok:
        log.critical(f'Status: {status.message}')
    assert status.ok
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
    log.debug(f'[DEBUG][mkdir] Status: {status}')
    if not status.ok:
        log.critical(f'Status: {status.message}')
    assert status.ok  # creation failed; RO redirector?

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
    log.debug(f'[DEBUG][locate] Status: {status}')
    if not status.ok:
        log.critical(f'Status: {status.message}')
    assert status.ok

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
    log.debug(f'[DEBUG][create file list] directory: {directory}')
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
