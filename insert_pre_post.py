import os
import os.path
import re
import sys

# TURNS OUT THAT ASYNC PROCESSING IS SLOWER... :/

# import asyncio
# import aiofiles
# 
# 
# MAX_OPEN_FILES = 1

def get_mathhub_dir(path, mayContainSymbLinks = True):
    ''' Extracts the MathHub directory from a path '''
    mathhub_dir = os.path.abspath(path)
    while not mathhub_dir.endswith('MathHub'):
        new = os.path.split(mathhub_dir)[0]
        if new == mathhub_dir:  # reached root
            if mayContainSymbLinks:
                return get_mathhub_dir(os.path.realpath(path), False)
            raise Exception('Failed to infer MathHub directory (it is required that a parent directory called "MathHub" exists)')
        mathhub_dir = new
    return mathhub_dir


def pre_process_archives(paths, mathhub_dir):
    for path in paths:
        if not os.path.isdir(os.path.join(path, '.git')): 
            print(f'Skipping {path} (not a git repo)')
        group, archive = os.path.split(os.path.relpath(path, mathhub_dir))
        yield {'path' : path, 'group' : group, 'archive' : archive}

def get_pre_post(group, mathhub_dir):
    path = lambda f : os.path.join(mathhub_dir, group, 'meta-inf', 'lib', f'{f}.tex')
    for c in ['pre', 'post']:
        if not os.path.isfile(path(c)):
            print(f'Skipping group {group}: No file "{path(c)}"')
            return None
    with open(path('pre'), 'r') as fp:
        pre = filter_ppp(fp.read())
    with open(path('post'), 'r') as fp:
        post = filter_ppp(fp.read())
        post = '\\libinput{post}\n'
    return (pre, post)


ppp_regex = re.compile(r'^ *\%\%\%[^\%].*$')
def filter_ppp(s):
    ''' removes %%%.* lines '''
    result = ''
    for line in s.splitlines():
        if not ppp_regex.match(line):
            result += line + '\n'
    return result


def get_tex_files_in_archive(archive):
    for dp, dn, fn in os.walk(os.path.join(archive['path'], 'source')):
        for f in fn:
            if f.endswith('.tex'):
                yield os.path.join(dp, f)

def get_tex_files_in_group(archives):
    for archive in archives:
        for f in get_tex_files_in_archive(archive):
            yield f




# def wrap_with_semaphore(semaphore):
#     def wrapper(func):
#         async def wrapped(*args, **kwargs):
#             async with semaphore:
#                 await func(*args, **kwargs)
#         return wrapped
#     return wrapper


# # @wrap_with_semaphore(semaphore)
# async def process_file(filename, pre, post, semaphore):
#     async with semaphore:
#         async with aiofiles.open(filename, 'r') as fp:
#             content = await fp.read()
#             if begindoc_regex.search(content):
#                 return 0    # doesn't require processing
#         async with aiofiles.open(filename, 'w') as fp:
#             await fp.write(pre + filter_ppp(content) + post)
#         return 1

begindoc_regex = re.compile(r'\\begin\{document\}')
localwords_regex = re.compile(r'^ *\% *LocalWords:.*$')
def process_file(filename, pre, post):
    localwords = ''
    content = ''
    with open(filename, 'r') as fp:
        for line in fp:
            if localwords_regex.match(line):
                localwords += line
            else: 
                content += line
    if begindoc_regex.search(content):
        return 0    # doesn't require processing
    with open(filename, 'w') as fp:
        fp.write(pre + filter_ppp(content) + post + localwords)
    return 1


# async def process_group(archives, pre, post):
#     semaphore = asyncio.Semaphore(MAX_OPEN_FILES)
#     tasks = []
#     for f in get_tex_files_in_group(archives):
#         tasks.append(process_file(f, pre, post, semaphore))
#     return (sum(await asyncio.gather(*tasks)), len(tasks))   # sum is number of changed files

def process_group(archives, pre, post):
    changed = 0
    total = 0
    for f in get_tex_files_in_group(archives):
        total += 1
        changed += process_file(f, pre, post)
    return (changed, total)


def main():
    if len(sys.argv) <= 1:
        print('No archives provided.')
        return
    paths = sys.argv[1:]
    mathhub_dir = get_mathhub_dir(paths[0])
    print(f'Inferred that {mathhub_dir} is the MathHub directory')
    archives = {}   # group : [archive]
    for archive in pre_process_archives(paths, mathhub_dir):
        if archive['group'] not in archives:
            archives[archive['group']] = []
        archives[archive['group']].append(archive)
    prepost = {}    # group : (pre, post)
    skipgroups = []
    for group in archives:
        pp = get_pre_post(group, mathhub_dir)
        if pp:
            prepost[group] = pp
        else:
            skipgroups.append(group)
    for s in skipgroups:
        del archives[s]

    for group in sorted(archives.keys()):
        print(f'Processing group "{group}"')
        # changed, total = asyncio.run(process_group(archives[group], prepost[group][0], prepost[group][1]))
        changed, total = process_group(archives[group], prepost[group][0], prepost[group][1])
        print(f'    Changed {changed} out of {total} files.')

if __name__ == '__main__':
    main()
