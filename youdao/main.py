# coding:utf-8
# -*- coding: utf-8 -*- 

import sys
import os
import shutil
import getopt
import requests
import json
import webbrowser
from collections import deque
from termcolor import colored
from spider import YoudaoSpider
from model import Word
import config

if sys.version_info.major == 3:
    from importlib import reload

# global unicode
# if sys.version_info[0] >= 3:
#     unicode = str

def show_result(result):
    """
    展示查询结果
    :param result: 与有道API返回的json 数据结构一致的dict
    """
    if 'stardict' in result:
        print(colored(u'StarDict:', 'blue'))
        print(result['stardict'])
        return

    if result['errorCode'] != 0:
        print(colored(YoudaoSpider.error_code[result['errorCode']], 'red'))
    else:
        print(colored('[%s]' % result['query'], 'magenta'))
        if 'basic' in result:
            if 'us-phonetic' in result['basic']:
                print(colored(u'美音:', 'blue'), colored('[%s]' % result['basic']['us-phonetic'], 'green'))
            if 'uk-phonetic' in result['basic']:
                print(colored(u'英音:', 'blue'), colored('[%s]' % result['basic']['uk-phonetic'], 'green'))
            if 'phonetic' in result['basic']:
                print(colored(u'拼音:', 'blue'), colored('[%s]' % result['basic']['phonetic'], 'green'))

            print(colored(u'基本词典:', 'blue'))
            print(colored('\t'+'\n\t'.join(result['basic']['explains']), 'yellow'))

        if 'translation' in result:
            print(colored(u'有道翻译:', 'blue'))
            print(colored('\t'+'\n\t'.join(str(result['translation'])), 'cyan'))

        if 'web' in result:
            print(colored(u'网络释义:', 'blue'))
            for item in result['web']:
                print('\t' + colored(item['key'], 'cyan') + ': ' + '; '.join(item['value']))


def play(voice_file):
    out1 = os.dup(1)
    out2 = os.dup(2)
    os.close(1)
    os.close(2)
    try:
        webbrowser.open(voice_file)
    finally:
        os.dup2(out1, 1)
        os.dup2(out2, 2)


def query(keyword, use_db=True, use_api=False, play_voice=False, use_dict=True):
    update_word = [True]
    word = Word.get_word(keyword)
    result = {'query': keyword, 'errorCode': 60}
    if use_db and word:
        result.update(json.loads(word.json_data))
        update_word[0] = False
    elif update_word[0]:
        # 从starditc中查找
        if use_dict and config.config.get('stardict'):
            try:
                from lib.cpystardict import Dictionary
            except ImportError:
                from lib.pystardict import Dictionary
            colors = deque(['cyan', 'yellow', 'blue'])
            stardict_base = config.config.get('stardict')
            stardict_trans = []
            for dic_dir in os.listdir(stardict_base):
                dic_file = os.listdir(os.path.join(stardict_base, dic_dir))[0]
                name, ext = os.path.splitext(dic_file)
                name = name.split('.')[0]
                dic = Dictionary(os.path.join(stardict_base, dic_dir, name))
                try:
                    # dic_exp = dic[keyword.encode("utf-8")]
                    dic_exp = dic[keyword]
                except KeyError:
                    pass
                else:
                    # dic_exp = unicode(dic_exp.decode('utf-8'))
                    stardict_trans.append(colored(u"[{dic}]:{word}".format(dic=name, word=keyword), 'green'))
                    color = colors.popleft()
                    colors.append(color)
                    stardict_trans.append(colored(dic_exp, color))
                    stardict_trans.append(colored(u'========================', 'magenta'))
            if stardict_trans:
                result['stardict'] = u'\n'.join(stardict_trans)
                result['errorCode'] = 0

        # 从stardict中没有匹配单词
        if not result['errorCode'] == 0:
            spider = YoudaoSpider(keyword)
            try:
                result.update(spider.get_result(use_api))
            except requests.HTTPError as e:
                print(colored(u'网络错误: %s' % e.message, 'red'))
                sys.exit()

        # 更新数据库
        new_word = word if word else Word()
        new_word.keyword = keyword
        new_word.json_data = json.dumps(result)
        new_word.save()

    show_result(result)
    if play_voice:
        print(colored(u'获取发音:{word}'.format(word=keyword), 'green'))
        voice_file = YoudaoSpider.get_voice(keyword)
        print(colored(u'获取成功,播放中...', 'green'))
        play(voice_file)


def show_db_list():
    print(colored(u'保存在数据库中的单词及查询次数:', 'blue'))
    for word in Word.select():
        print(colored(word.keyword, 'cyan'), colored(str(word.count), 'green'))

def show_today_list(args):
    days = int(args)
    print(colored(u'近%d天内查询的单词:'%(days), 'blue'))
    for word in Word.get_today_words(days):
        print(colored(word.keyword, 'cyan'), colored(str(word.count), 'green'))


def del_word(keyword):
    if keyword:
        try:
            word = Word.select().where(Word.keyword == keyword).get()
            word.delete_instance()
            print(colored(u'已删除{0}'.format(keyword), 'blue'))
        except Word.DoesNotExist:
            print(colored(u'没有找到{0}'.format(keyword), 'red'))
        config.silent_remove(os.path.join(config.VOICE_DIR, keyword+'.mp3'))
    else:
        count = Word.delete().execute()
        shutil.rmtree(config.VOICE_DIR, ignore_errors=True)
        print(colored(u'共删除{0}个单词'.format(count), 'blue'))


def show_help():
    desc = '''
    == 说明 ==

    * 功能描述

    获取查询结果有两种方式：
    1. 使用api的方式，直接返回json字符串
    2. 使用页面方式，则需要借用BeautifulSoup解析返回的html
    PS. 如果以上查询都失败（比如给句子加上标点），则使用有道翻译

    查询记录保存在peewee数据库中，所有基于db的操作都与此有关
    离线字典保存的目录，由config.config['stardict']指定

    * 可选参数

    -a          使用有道api查询，参考官网 http://fanyi.youdao.com/openapi?path=data-mode
    -n          不用数据库中缓存的查询记录
    -l          列出查询记录及累计次数
    -t [day]    列出近几天查过的单词
    -d [key]    删除制定文本的查询记录，包括发音文件
    -c          删除所有的查询记录，包括发音文件
    -v          查询并播放发音，可使用 yd -v 重复播放上一查询记录的发音
    -s [path]   指定离线字典的目录，默认为/dicts
    -y          完全的在线查询。既不使用数据库查询记录，也不使用离线字典
    '''
    print(desc)


def main():
    reload(sys)
        
    config.prepare()
    try:
        options, args = getopt.getopt(sys.argv[1:], 'anlt:d:cvs:y', ['help'])
    except getopt.GetoptError:
        options = [('--help', '')]
    if ('--help', '') in options:
        show_help()
        return

    use_api = False
    use_db = True
    play_voice = False
    use_dict = True
    # print(options)
    for opt in options:
        if opt[0] == '-a':
            use_api = True
        elif opt[0] == '-n':
            use_db = False
        elif opt[0] == '-l':
            show_db_list()
            sys.exit()
        elif opt[0] == '-t':
            show_today_list(opt[1])
            sys.exit()
        elif opt[0] == '-d':
            del_word(opt[1])
            sys.exit()
        elif opt[0] == '-c':
            del_word(None)
            sys.exit()
        elif opt[0] == '-v':
            play_voice = True
        elif opt[0] == '-s':
            if os.path.isdir(opt[1]):
                print(u'stardict 路径设置成功：', opt[1])
                config.set_dict_path(opt[1])
            else:
                print(u'stardict 路径设置失败. 原因可能是路径"%s"不存在.' % opt[1])
            sys.exit()
        elif opt[0] == '-y':
            use_dict = False
            use_db = False
    
    dict_path = os.path.join(config.HOME, "dicts")
    config.set_dict_path(dict_path)

    # keyword = unicode(' '.join(args), encoding=sys.getfilesystemencoding())
    # keyword = unicode(' '.join(args), encoding='utf-8')
    keyword = ' '.join(args)

    if not keyword:
        if play_voice:
            word = Word.get_last_word()
            keyword = word.keyword
            query(keyword, play_voice=True, use_db=True)
        else:
            show_help()
    else:
        query(keyword, use_db, use_api, play_voice, use_dict)

if __name__ == '__main__':
    main()
