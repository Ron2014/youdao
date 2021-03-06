# coding: utf-8

import sys
import os
import errno

if sys.version_info.major == 3:
    import _pickle as cPickle
else:
    import cPickle

VERSION = '0.3.1'
'''
Windows: E:/GitHub/youdao-ME/youdao
Ubuntu/Macbook: $HOME/Document/GitHub/youdao-ME/youdao
Docker(Ubuntu/mount): $HOME/youdao
'''
HOME = os.environ.get("GITHUB_PATH")
assert HOME, "unknow platform %s for ENV ${GITHUB_PATH}" % (sys.platform)
HOME = os.path.join(HOME, "youdao-ME/youdao")
# print("===================", HOME)

BASE_DIR = os.path.join(HOME, '.dict_youdao')   # 用户数据根目录
VOICE_DIR = os.path.join(BASE_DIR, 'voice')     # 音频文件

DATABASE = 'youdao.db'
PK_FILE = 'youdao.pk'
DB_DIR = os.path.join(BASE_DIR, DATABASE)
PK_DIR = os.path.join(BASE_DIR, PK_FILE)

config = {'version': '0'}


def silent_remove(filename):
    try:
        os.remove(filename)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise


def save_config():
    with open(PK_DIR, 'wb') as f:
        cPickle.dump(config, f)


def update():
    # 从0.2.0开始更改了数据库
    # 重新设置数据库
    if config.get('version', '0') < '0.2.0':
        # silent_remove(DB_DIR)
        from model import db, Word
        db.drop_table(Word, fail_silently=True)
        Word.create_table()


def prepare():
    if not os.path.exists(BASE_DIR):
        os.mkdir(BASE_DIR)
    if not os.path.exists(VOICE_DIR):
        os.mkdir(VOICE_DIR)

    if os.path.isfile(PK_DIR):
        with open(PK_DIR, 'rb') as f:
            global config
            config = cPickle.load(f)
    # update
    update()
    if config.get('version', '0') < VERSION:
        config['version'] = VERSION
        save_config()


def set_dict_path(path):
    config['stardict'] = path
    save_config()
